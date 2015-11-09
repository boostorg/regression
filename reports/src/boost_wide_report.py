
# Copyright (c) MetaCommunications, Inc. 2003-2007
#
# Distributed under the Boost Software License, Version 1.0. 
# (See accompanying file LICENSE_1_0.txt or copy at 
# http://www.boost.org/LICENSE_1_0.txt)

import shutil
import codecs
import xml.sax.handler
import xml.sax.saxutils
import glob
import re
import os.path
import os
import string
import time
import sys
import ftplib

import utils

#===============================================================================
# The entry point is the boost_wide_report.py script. In the simplest
# case, it should be run as:
# 
#      python boost_wide_report.py 
#            --locate-root=XXX  
#            --results-dir=YYY
#            --tag trunk
#            --expected-results=XXX
#            --failures-markup=XXX 
# 
# The 'trunk' is the tag of things that are tested, and should match the
# directory name on the server keeping uploaded individual results.
# 'results-dir' is a directory where individual results (zip files) will
# be downloaded, and then processed. expected-results and failures-markup
# should be paths to corresponding files in 'status' subdir of boost tree.
# locate-root should point at boost root, it's unclear if it of any use
# now.
# 
# This will download and process *all* test results, but it will not
# upload them, so good for local testing. It's possible to run
# this command, interrupt it while it processes results, leave just
# a few .zip files in result dir, and then re-run with --dont-collect-logs
# option, to use downloaded zips only.
#===============================================================================

report_types = [ 'us', 'ds', 'ud', 'dd', 'l', 'p', 'i', 'n', 'ddr', 'dsr', 'udr', 'usr' ]

default_filter_runners = {
    'master' : [
        'Sandia-.*',
        'BP.*',
        'DebSid.*',
        'Debian-Sid',
        'PNNL-.*',
        'teeks99-.*',
        'NA-QNX.*',
        '.*jc-bell',
        'CrystaX.*',
        'marshall-.*',
        'GLIS.*',
        'jessicah-haiku.*',
        'oracle-.*',
        'igaztanaga.*',
        ]
    }

# How long results are considered , in seconds = 4 weeks
result_decay_time_seconds = 60*60*24*7*4

if __name__ == '__main__':
    run_dir = os.path.abspath( os.path.dirname( sys.argv[ 0 ] ) )
else:
    run_dir = os.path.abspath( os.path.dirname( sys.modules[ __name__ ].__file__ ) )


def map_path( path ):
    return os.path.join( run_dir, path ) 

class file_info:
    def __init__( self, file_name, file_size, file_date ):
        self.name = file_name
        self.size = file_size
        self.date = file_date

    def __repr__( self ):
        return "name: %s, size: %s, date %s" % ( self.name, self.size, self.date )

#
# Find the mod time from unix format directory listing line
#

def get_date( f, words ):
    # f is an ftp object

    (response, modtime) = f.sendcmd('MDTM %s' % words[-1]).split( None, 2 )
    year = int( modtime[0:4] )
    month = int( modtime[4:6] )
    day = int( modtime[6:8] )
    hours = int( modtime[8:10] )
    minutes = int( modtime[10:12] )
    seconds = int( modtime[12:14] )
    return ( year, month, day, hours, minutes, seconds, 0, 0, 0)

def list_ftp( f, filter_runners = None ):
    # f is an ftp object
    utils.log( "listing source content" )
    lines = []

    # 1. get all lines
    f.dir( lambda x: lines.append( x ) )

    # 2. split lines into words
    word_lines = [ x.split( None, 8 ) for x in lines ]

    if filter_runners != None:
        if isinstance(filter_runners, list):
            runners = []
            for word_line in word_lines:
                for filter_runner in filter_runners:
                    if re.match(filter_runner, word_line[-1], re.IGNORECASE):
                        utils.log("    matched runner '%s' with filter '%s'"%(word_line[-1], filter_runner))
                        runners.append(word_line)
                        break
            word_lines = runners
        else:
            word_lines = [ x for x in word_lines if re.match( filter_runners, x[-1], re.IGNORECASE ) ]

    # we don't need directories
    result = [ file_info( l[-1], int( l[4] ), get_date( f, l ) ) for l in word_lines if l[0][0] != "d" ]
    
    # we discard old results
    recent_results = []
    current_t = time.time()
    for r in result:
        t = mkgmtime(r.date)
        if current_t-t <= result_decay_time_seconds:
            recent_results.append(r)
    result = recent_results
    
    for f in result:
        utils.log( "    %s" % f )
    return result

def list_dir( dir ):
    utils.log( "listing destination content %s" % dir )
    result = []
    for file_path in glob.glob( os.path.join( dir, "*.zip" ) ):
        if os.path.isfile( file_path ):
            mod_time = time.gmtime( os.path.getmtime( file_path ) )
            mod_time = ( mod_time[0], mod_time[1], mod_time[2], mod_time[3], mod_time[4], mod_time[5], 0, 0, mod_time[8] )
            size = os.path.getsize( file_path )
            result.append( file_info( os.path.basename( file_path ), size, mod_time ) )
    for fi in result:
        utils.log( "    %s" % fi )
    return result

def find_by_name( d, name ):
    for dd in d:
        if dd.name == name:
            return dd
    return None

# Proof:
# gmtime(result) = time_tuple
# mktime(gmtime(result)) = mktime(time_tuple)
# correction = mktime(gmtime(result)) - result
# result = mktime(time_tuple) - correction
def mkgmtime(time_tuple):
    # treat the tuple as if it were local time
    local = time.mktime(time_tuple)
    # calculate the correction to get gmtime
    old_correction = 0
    correction = time.mktime(time.gmtime(local)) - local
    result = local
    # iterate until the correction doesn't change
    while correction != old_correction:
        old_correction = correction
        correction = time.mktime(time.gmtime(result)) - result
        result = local - correction
    return result

def diff( source_dir_content, destination_dir_content ):
    utils.log( "Finding updated files" )
    result = ( [], [] ) # ( changed_files, obsolete_files )
    for source_file in source_dir_content:
        found = find_by_name( destination_dir_content, source_file.name )
        if found is None: result[0].append( source_file.name )
        elif time.mktime( found.date ) != time.mktime( source_file.date ) or \
             found.size != source_file.size:
            result[0].append( source_file.name )
        else:
            pass
    for destination_file in destination_dir_content:
        found = find_by_name( source_dir_content, destination_file.name )
        if found is None: result[1].append( destination_file.name )
    utils.log( "   Updated files:" )
    for f in result[0]:
        utils.log( "    %s" % f )
    utils.log( "   Obsolete files:" )
    for f in result[1]:
        utils.log( "    %s" % f )
    return result
        
def _modtime_timestamp( file ):
    return os.stat( file ).st_mtime
                

root_paths = []

def shorten( file_path ):
    root_paths.sort( lambda x, y: cmp( len(y ), len( x ) ) )
    for root in root_paths:
        if file_path.lower().startswith( root.lower() ):
            return file_path[ len( root ): ].replace( "\\", "/" )
    return file_path.replace( "\\", "/" )

class action:
    def __init__( self, file_path ):
        self.file_path_ = file_path
        self.relevant_paths_ = [ self.file_path_ ]
        self.boost_paths_ = []
        self.dependencies_ = []
        self.other_results_ = []

    def run( self ):
        utils.log( "%s: run" % shorten( self.file_path_ ) )
        __log__ = 2

        for dependency in self.dependencies_:
            if not os.path.exists( dependency ):
                utils.log( "%s doesn't exists, removing target" % shorten( dependency ) )
                self.clean()
                return

        if not os.path.exists( self.file_path_ ):
            utils.log( "target doesn't exists, building" )            
            self.update()
            return

        dst_timestamp = _modtime_timestamp( self.file_path_ )
        utils.log( "    target: %s [%s]" % ( shorten( self.file_path_ ),  dst_timestamp ) )
        needs_updating = 0
        utils.log( "    dependencies:" )
        for dependency in  self.dependencies_:
            dm = _modtime_timestamp( dependency )
            update_mark = ""
            if dm > dst_timestamp:
                needs_updating = 1
            utils.log( '        %s [%s] %s' % ( shorten( dependency ), dm, update_mark ) )
            
        if  needs_updating:
            utils.log( "target needs updating, rebuilding" )            
            self.update()
            return
        else:
            utils.log( "target is up-to-date" )            


    def clean( self ):
        to_unlink = self.other_results_ + [ self.file_path_ ]
        for result in to_unlink:
            utils.log( '  Deleting obsolete "%s"' % shorten( result ) )
            if os.path.exists( result ):
                os.unlink( result )
    
class unzip_action( action ):
    def __init__( self, source, destination, unzip_func ):
        action.__init__( self, destination )
        self.dependencies_.append( source )
        self.source_     = source
        self.unzip_func_ = unzip_func

    def update( self ):
        try:
            utils.log( '  Unzipping "%s" ... into "%s"' % ( shorten( self.source_ ), os.path.dirname( self.file_path_ ) ) )
            self.unzip_func_( self.source_, os.path.dirname( self.file_path_ ) )
        except Exception, msg:
            utils.log( '  Skipping "%s" due to errors (%s)' % ( self.source_, msg ) )


def ftp_task( site, site_path , destination, filter_runners = None ):
    __log__ = 1
    utils.log( '' )
    utils.log( 'ftp_task: "ftp://%s/%s" -> %s' % ( site, site_path, destination ) )

    utils.log( '    logging on ftp site %s' % site )
    f = ftplib.FTP( site )
    f.login()
    utils.log( '    cwd to "%s"' % site_path )
    f.cwd( site_path )

    source_content = list_ftp( f, filter_runners )
    source_content = [ x for x in source_content if re.match( r'.+[.](?<!log[.])zip', x.name ) and x.name.lower() != 'boostbook.zip' ]
    destination_content = list_dir( destination )
    d = diff( source_content, destination_content )

    def synchronize():
        for source in d[0]:
            utils.log( 'Copying "%s"' % source )
            result = open( os.path.join( destination, source ), 'wb' )
            f.retrbinary( 'RETR %s' % source, result.write )
            result.close()
            mod_date = find_by_name( source_content, source ).date
            m = mkgmtime( mod_date )
            os.utime( os.path.join( destination, source ), ( m, m ) )

        for obsolete in d[1]:
            utils.log( 'Deleting "%s"' % obsolete )
            os.unlink( os.path.join( destination, obsolete ) )

    utils.log( "    Synchronizing..." )
    __log__ = 2
    synchronize()
    
    f.quit()        

def unzip_archives_task( source_dir, processed_dir, unzip_func ):
    utils.log( '' )
    utils.log( 'unzip_archives_task: unpacking updated archives in "%s" into "%s"...' % ( source_dir, processed_dir ) )
    __log__ = 1

    target_files = [ os.path.join( processed_dir, os.path.basename( x.replace( ".zip", ".xml" ) )  ) for x in glob.glob( os.path.join( source_dir, "*.zip" ) ) ] + glob.glob( os.path.join( processed_dir, "*.xml" ) )
    actions = [ unzip_action( os.path.join( source_dir, os.path.basename( x.replace( ".xml", ".zip" ) ) ), x, unzip_func ) for x in target_files ]
    for a in actions:
        a.run()
   
class xmlgen( xml.sax.saxutils.XMLGenerator ):
    document_started = 0
    
    def startDocument( self ):
        if not self.document_started:
            xml.sax.saxutils.XMLGenerator.startDocument( self )
            self.document_started = 1


def execute_tasks(
          tag
        , user
        , run_date
        , comment_file
        , results_dir
        , output_dir
        , reports
        , warnings
        , extended_test_results
        , dont_collect_logs
        , expected_results_file
        , failures_markup_file
        , report_executable
        , filter_runners
        ):

    incoming_dir = os.path.join( results_dir, 'incoming', tag )
    processed_dir = os.path.join( incoming_dir, 'processed' )
    merged_dir = os.path.join( processed_dir, 'merged' )
    if not os.path.exists( incoming_dir ):
        os.makedirs( incoming_dir )
    if not os.path.exists( processed_dir ):
        os.makedirs( processed_dir )
    if not os.path.exists( merged_dir ):
        os.makedirs( merged_dir )
    
    if not dont_collect_logs:
        ftp_site = 'boost.cowic.de'
        site_path = '/boost/do-not-publish-this-url/results/%s' % tag

        ftp_task( ftp_site, site_path, incoming_dir, filter_runners )

    unzip_archives_task( incoming_dir, processed_dir, utils.unzip )

    if not os.path.exists( merged_dir ):
        os.makedirs( merged_dir )

    command_line = report_executable
    command_line += " --expected " + '"%s"' % expected_results_file 
    command_line += " --markup " + '"%s"' % failures_markup_file
    command_line += " --comment " + '"%s"' % comment_file
    command_line += " --tag " + tag
    # command_line += " --run-date " + '"%s"' % run_date
    command_line += " -rl"
    for r in reports:
        command_line += ' -r' + r
    command_line += " --css " + map_path( 'master.css' )

    for f in glob.glob( os.path.join( processed_dir, '*.xml' ) ):
        command_line += ' "%s"' % f

    utils.log("Producing the reports...")
    utils.log("> "+command_line)
    os.system(command_line)

        
def build_reports( 
          locate_root_dir
        , tag
        , expected_results_file
        , failures_markup_file
        , comment_file
        , results_dir
        , result_file_prefix
        , dont_collect_logs = 0
        , reports = report_types
        , report_executable = None
        , warnings = []
        , user = None
        , upload = False
        , filter_runners = None
        ):

    ( run_date ) = time.strftime( '%Y-%m-%dT%H:%M:%SZ', time.gmtime() )

    root_paths.append( locate_root_dir )
    root_paths.append( results_dir )
    
    bin_boost_dir = os.path.join( locate_root_dir, 'bin', 'boost' )
    
    output_dir = os.path.join( results_dir, result_file_prefix )
    utils.makedirs( output_dir )
    
    if expected_results_file != '':
        expected_results_file = os.path.abspath( expected_results_file )
    else:
        expected_results_file = os.path.abspath( map_path( 'empty_expected_results.xml' ) )


    extended_test_results = os.path.join( output_dir, 'extended_test_results.xml' )
    
    if filter_runners == None:
        if default_filter_runners.has_key(tag):
            filter_runners = default_filter_runners[tag]
        
    execute_tasks(
          tag
        , user
        , run_date
        , comment_file
        , results_dir
        , output_dir
        , reports
        , warnings
        , extended_test_results
        , dont_collect_logs
        , expected_results_file
        , failures_markup_file
        , report_executable
        , filter_runners
        )

    if upload:
        upload_dir = 'regression-logs/'
        utils.log( 'Uploading  results into "%s" [connecting as %s]...' % ( upload_dir, user ) )
        
        archive_name = '%s.tar.gz' % result_file_prefix
        utils.tar( 
              os.path.join( results_dir, result_file_prefix )
            , archive_name
            )
        
        utils.sourceforge.upload( os.path.join( results_dir, archive_name ), upload_dir, user )
        utils.sourceforge.untar( os.path.join( upload_dir, archive_name ), user, background = True )


def accept_args( args ):
    args_spec = [ 
          'locate-root='
        , 'tag='
        , 'expected-results='
        , 'failures-markup='
        , 'comment='
        , 'results-dir='
        , 'results-prefix='
        , 'dont-collect-logs'
        , 'reports='
        , 'boost-report='
        , 'user='
        , 'upload'
        , 'help'
        , 'filter-runners='
        ]
        
    options = { 
          '--comment': ''
        , '--expected-results': ''
        , '--failures-markup': ''
        , '--reports': string.join( report_types, ',' )
        , '--boost-report': None
        , '--tag': None
        , '--user': None
        , 'upload': False
        , '--filter-runners': None
        }
    
    utils.accept_args( args_spec, args, options, usage )
    if not options.has_key( '--results-dir' ):
         options[ '--results-dir' ] = options[ '--locate-root' ]

    if not options.has_key( '--results-prefix' ):
        options[ '--results-prefix' ] = 'all'

    warnings = []
    
    return ( 
          options[ '--locate-root' ]
        , options[ '--tag' ]
        , options[ '--expected-results' ]
        , options[ '--failures-markup' ]
        , options[ '--comment' ]
        , options[ '--results-dir' ]
        , options[ '--results-prefix' ]
        , options.has_key( '--dont-collect-logs' )
        , options[ '--reports' ].split( ',' )
        , options[ '--boost-report' ]
        , warnings
        , options[ '--user' ]
        , options.has_key( '--upload' )
        , options[ '--filter-runners' ]
        )


def usage():
    print 'Usage: %s [options]' % os.path.basename( sys.argv[0] )
    print    '''
\t--locate-root         the same as --locate-root in compiler_status
\t--tag                 the tag for the results (i.e. 'trunk')
\t--expected-results    the file with the results to be compared with
\t                      the current run
\t--failures-markup     the file with the failures markup
\t--comment             an html comment file (will be inserted in the reports)
\t--results-dir         the directory containing -links.html, -fail.html
\t                      files produced by compiler_status (by default the
\t                      same as specified in --locate-root)
\t--results-prefix      the prefix of -links.html, -fail.html
\t                      files produced by compiler_status
\t--user                SourceForge user name for a shell account
\t--upload              upload reports to SourceForge 

The following options are useful in debugging:

\t--dont-collect-logs dont collect the test logs
\t--reports           produce only the specified reports
\t                        us - user summary
\t                        ds - developer summary
\t                        ud - user detailed
\t                        dd - developer detailed
\t                        l  - links
\t                        p  - patches
\t                        x  - extended results file
\t                        i  - issues
\t                        n  - runner comment files
\t--filter-runners    use only those runners that match specified
\t                    regex (case insensitive)
'''

def main():
    build_reports( *accept_args( sys.argv[ 1 : ] ) )

if __name__ == '__main__':
    main()
