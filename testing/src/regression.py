#!/usr/bin/env python

# Copyright MetaCommunications, Inc. 2003-2007
# Copyright Rene Rivera 2007-2015
#
# Distributed under the Boost Software License, Version 1.0.
# (See accompanying file LICENSE_1_0.txt or copy at
# http://www.boost.org/LICENSE_1_0.txt)

import glob
import inspect
import optparse
import os
import os.path
import platform
import sys
import time

git_info = {
    'build' : {
        'git' : 'https://github.com/boostorg/build.git',
        'dir' : 'boost_bb',
        'subdir' : '',
        },
    'regression' : {
        'git' : 'https://github.com/boostorg/regression.git',
        'dir' : 'boost_regression',
        'subdir' : '',
        'branch' : 'develop',
        },
    'boost-build.jam' : {
        'raw' : 'https://raw.githubusercontent.com/boostorg/boost/%s/boost-build.jam'
        },
    'boost' : {
        'git' : 'https://github.com/boostorg/boost.git',
        'dir' : 'boost_root',
        'subdir' : '',
        },
    }

git_branch = {
    'trunk' : 'develop',
    'release' : 'master',
    'develop' : 'develop',
    'master' : 'master',
    }

class utils:

    @staticmethod
    def system( commands ):
        if sys.platform == 'win32':
            f = open( 'tmp.cmd', 'w' )
            f.write( "".join( commands, '\n' ) )
            f.close()
            rc = os.system( 'tmp.cmd' )
            return rc
        else:
            rc = os.system( '&&'.join( commands ) )
            return rc


    @staticmethod
    def checked_system( commands, valid_return_codes = [ 0 ] ):
        rc = utils.system( commands )
        if rc not in [ 0 ] + valid_return_codes:
            raise Exception( 'Command sequence "%s" failed with return code %d' % ( commands, rc ) )
        return rc

    @staticmethod
    def makedirs( path ):
        if not os.path.exists( path ):
            os.makedirs( path )

    @staticmethod
    def log_level():
       frames = inspect.stack()
       level = 0
       for i in frames[ 3: ]:
           if i[0].f_locals.has_key( '__log__' ):
               level = level + i[0].f_locals[ '__log__' ]
       return level

    @staticmethod
    def log( message ):
        sys.stderr.write( '# ' + '    ' * utils.log_level() +  message + '\n' )
        sys.stderr.flush()

class runner:

    def __init__(self,root):
        commands = list(map(
            lambda m: m[8:].replace('_','-'),
            filter(
                lambda m: m.startswith('command_'),
                runner.__dict__.keys())
            ))
        commands.sort()
        commands = "commands: %s" % ', '.join(commands)

        opt = optparse.OptionParser(
            usage="%prog [options] [commands]",
            description=commands)

        #~ Base Options:
        opt.add_option( '--runner',
            help="runner ID (e.g. 'Metacomm')" )
        opt.add_option( '--comment',
            help="an HTML comment file to be inserted in the reports" )
        opt.add_option( '--tag',
            help="the tag for the results" )
        opt.add_option( '--group',
            help="the group in which the results are reported, defaults to the tag")
        opt.add_option( '--toolsets',
            help="comma-separated list of toolsets to test with" )
        opt.add_option( '--libraries',
            help="comma separated list of libraries to test")
        opt.add_option( '--incremental',
            help="do incremental run (do not remove previous binaries)",
            action='store_true' )
        opt.add_option( '--timeout',
            help="specifies the timeout, in minutes, for a single test run/compilation",
            type='int' )
        opt.add_option( '--bjam-options',
            help="options to pass to the regression test" )
        opt.add_option( '--bjam-toolset',
            help="bootstrap toolset for 'bjam' executable" )
        opt.add_option( '--pjl-toolset',
            help="bootstrap toolset for 'process_jam_log' executable" )
        opt.add_option( '--platform' )

        #~ Source Options:
        opt.add_option( '--local',
            help="the name of the boost tarball" )
        opt.add_option( '--force-update',
            help="do an update (if applicable) instead of a clean checkout, even when performing a full run",
            action='store_true' )
        opt.add_option( '--have-source',
            help="do neither a tarball download nor a repo update; used primarily for testing script changes",
            action='store_true' )
        opt.add_option( '--use-dulwich',
            help="use dulwich git implementation for git access",
            action='store_true')

        #~ Connection Options:
        opt.add_option( '--ftp',
            help="FTP URL to upload results to." )
        opt.add_option( '--proxy',
            help="HTTP proxy server address and port (e.g.'http://www.someproxy.com:3128')" )
        opt.add_option( '--ftp-proxy',
            help="FTP proxy server (e.g. 'ftpproxy')" )
        opt.add_option( '--dart-server',
            help="the dart server to send results to" )

        #~ Debug Options:
        opt.add_option( '--debug-level',
            help="debugging level; controls the amount of debugging output printed",
            type='int' )
        opt.add_option( '--send-bjam-log',
            help="send full bjam log of the regression run",
            action='store_true' )
        opt.add_option( '--mail',
            help="email address to send run notification to" )
        opt.add_option( '--smtp-login',
            help="STMP server address/login information, in the following form: <user>:<password>@<host>[:<port>]" )
        opt.add_option( '--skip-tests',
            help="do not run bjam; used for testing script changes",
            action='store_true' )
        opt.add_option( '--verbose-log-processing',
            help="enable verbose processing of bjam logs",
            action='store_true' )

        #~ Defaults
        self.runner = None
        self.comment='comment.html'
        self.tag='develop'
        self.group=None
        self.toolsets=None
        self.libraries=None
        self.incremental=False
        self.timeout=5
        self.bjam_options=''
        self.bjam_toolset=''
        self.pjl_toolset=''
        self.platform=self.platform_name()
        self.local=None
        self.force_update=False
        self.have_source=False
        self.ftp=None
        self.proxy=None
        self.ftp_proxy=None
        self.dart_server=None
        self.debug_level=0
        self.send_bjam_log=False
        self.mail=None
        self.smtp_login=None
        self.skip_tests=False
        self.use_git=True
        self.use_dulwich=False
        self.verbose_log_processing=False
        ( _opt_, self.actions ) = opt.parse_args(None,self)
        if not self.actions or self.actions == []:
            self.actions = [ 'regression' ]

        #~ Set the reporting group if it wasn't specified.
        if not self.group:
            self.group = self.git_branch()

        #~ Initialize option dependent values.
        self.regression_root = root

        #~ Boost paths.
        self.boost_root = os.path.join( self.regression_root, 'boost_root' )
        self.regression_results = os.path.join( self.regression_root, 'results' )
        if self.pjl_toolset != 'python':
            self.regression_log = os.path.join( self.regression_results, 'bjam.log' )
        else:
            self.regression_log = os.path.join( self.regression_results, 'bjam.xml' )

        #~ Boost Build paths.
        self.tools_bb_root = os.path.join( self.regression_root,'boost_bb' )
        self.tools_bb_root = os.path.join( self.tools_bb_root, 'src')
        self.tools_bjam_root = os.path.join( self.regression_root,'boost_bb', 'src', 'engine' )

        #~ Regression tools paths.
        self.tools_regression_root = os.path.join( self.regression_root,'boost_regression' )
        self.xsl_reports_dir = os.path.join( self.tools_regression_root, 'xsl_reports' )

        self.timestamp_path = os.path.join( self.regression_root, 'timestamp' )
        if sys.platform == 'win32':
            self.patch_boost = 'patch_boost.bat'
            self.bjam = { 'name' : 'bjam.exe' }
            self.process_jam_log = { 'name' : 'process_jam_log.exe' }
        elif sys.platform == 'cygwin':
            self.patch_boost = 'patch_boost'
            self.bjam = { 'name' : 'b2.exe' }
            self.process_jam_log = { 'name' : 'process_jam_log.exe' }
        else:
            self.patch_boost = 'patch_boost'
            self.bjam = { 'name' : 'b2' }
            self.process_jam_log = { 'name' : 'process_jam_log' }
        self.bjam = {
            'name' : self.bjam['name'],
            'build_cmd' : self.bjam_build_cmd,
            'path' : os.path.join(self.regression_root,self.bjam['name']),
            'source_dir' : self.tools_bjam_root,
            'build_dir' : self.tools_bjam_root,
            'build_args' : ''
            }
        self.process_jam_log = {
            'name' : self.process_jam_log['name'],
            'build_cmd' : self.bjam_cmd,
            'path' : os.path.join(self.tools_regression_root,'stage','bin',self.process_jam_log['name']),
            'source_dir' : os.path.join(self.tools_regression_root,'testing','build'),
            'build_dir' : os.path.join(self.tools_regression_root,'stage','bin'),
            'build_args' : 'install -d2'
            }

        if self.debug_level > 0:
            self.log('Regression root =     %s'%self.regression_root)
            self.log('Boost root =          %s'%self.boost_root)
            self.log('Regression results =  %s'%self.regression_results)
            self.log('Regression log =      %s'%self.regression_log)
            self.log('BB root =             %s'%self.tools_bb_root)
            self.log('Bjam root =           %s'%self.tools_bjam_root)
            self.log('Tools root =          %s'%self.tools_regression_root)
            self.log('XSL reports dir =     %s'%self.xsl_reports_dir)
            self.log('Timestamp =           %s'%self.timestamp_path)
            self.log('Patch Boost script =  %s'%self.patch_boost)

        if self.libraries is not None:
            self.libraries = self.libraries.split(",")
            # Boost.Build depends on any having run
            if "build" in self.libraries and "any" not in self.libraries:
                self.libraries += ["any"]

            self.bjam_options += ' "--limit-tests=' + \
                "|".join(lib for lib in self.libraries if lib != "build") + '"'

        # if no -m bjam option add -m64 (limit target to 64 kb of output)
        import re
        if not [e for e in re.split('\s+', self.bjam_options) if e.startswith('-m')]:
            self.bjam_options += ' -m64'

        self.main()

    #~ The various commands that make up the testing sequence...

    def command_cleanup(self,*args):
        if not args or args == None or args == []: args = [ 'source', 'bin' ]

        if 'source' in args:
            self.log( 'Cleaning up "%s" directory ...' % self.boost_root )
            self.git_source_checkout(True)

        if 'bin' in args:
            boost_bin_dir = os.path.join( self.boost_root, 'bin' )
            self.log( 'Cleaning up "%s" directory ...' % boost_bin_dir )
            self.rmtree( boost_bin_dir )

            boost_binv2_dir = os.path.join( self.boost_root, 'bin.v2' )
            self.log( 'Cleaning up "%s" directory ...' % boost_binv2_dir )
            self.rmtree( boost_binv2_dir )

            self.log( 'Cleaning up "%s" directory ...' % self.regression_results )
            self.rmtree( self.regression_results )

    def command_get_tools(self):
        #~ Get Boost.Build v2...
        self.log( 'Getting Boost.Build v2...' )
        self.git_checkout(
            git_info['build'],
            self.git_branch())
        #~ Get the regression tools and utilities...
        self.log( 'Getting regression tools and utilities...' )
        self.git_checkout(
            git_info['regression'],
            git_info['regression']['branch'])
        #~ We get a boost-build.jam to make the tool build work even if there's
        #~ an existing boost-build.jam above the testing root.
        self.log( 'Getting boost-build.jam...' )
        self.http_get(
            git_info['boost-build.jam']['raw']%(self.git_branch()),
            os.path.join(self.regression_root, 'boost-build.jam') )

    def command_get_source(self):
        self.refresh_timestamp()
        self.log( 'Getting sources (%s)...' % self.timestamp() )
        self.retry(self.git_source_checkout)
        pass

    def command_update_source(self):
        self.refresh_timestamp()
        self.log( 'Updating sources (%s)...' % self.timestamp() )
        self.retry(self.git_source_checkout)
        pass

    def command_patch(self):
        patch_boost_path = os.path.join( self.regression_root, self.patch_boost )
        if os.path.exists( patch_boost_path ):
            self.log( 'Found patch file "%s". Executing it.' % patch_boost_path )
            os.chdir( self.regression_root )
            utils.system( [ patch_boost_path ] )
        pass

    def command_setup(self):
        self.command_patch()
        self.build_if_needed(self.bjam,self.bjam_toolset)
        if self.pjl_toolset != 'python':
            self.build_if_needed(self.process_jam_log,self.pjl_toolset)

    def command_test(self, *args):
        if not args or args == None or args == []: args = [ "test", "process" ]

        self.log( 'Making "%s" directory...' % self.regression_results )
        utils.makedirs( self.regression_results )

        results_libs = os.path.join( self.regression_results, 'libs' )
        results_status = os.path.join( self.regression_results, 'status' )

        if "clean" in args:
            self.command_test_clean()

        if "test" in args:
            self.command_test_run()
            self.command_test_boost_build()

        if "process" in args:
            if self.pjl_toolset != 'python':
                self.command_test_process()

    def command_test_clean(self):
        results_libs = os.path.join( self.regression_results, 'libs' )
        results_status = os.path.join( self.regression_results, 'status' )
        self.rmtree( results_libs )
        self.rmtree( results_status )

    def command_test_run(self):
        if self.pjl_toolset != 'python':
            test_cmd = '%s -d2 preserve-test-targets=off --dump-tests %s "--build-dir=%s" >>"%s" 2>&1' % (
                self.bjam_cmd( self.toolsets ),
                self.bjam_options,
                self.regression_results,
                self.regression_log )
        else:
            test_cmd = '%s -d1 preserve-test-targets=off --dump-tests --verbose-test %s "--build-dir=%s" "--out-xml=%s"' % (
                self.bjam_cmd( self.toolsets ),
                self.bjam_options,
                self.regression_results,
                self.regression_log )
        headers_cmd = self.bjam_cmd(None, 'headers')
        cd = os.getcwd()
        self.log( 'Updating headers (%s)...' % headers_cmd )
        os.chdir( self.boost_root )
        utils.system( [ headers_cmd ] )
        self.log( 'Starting tests (%s)...' % test_cmd )
        os.chdir( os.path.join( self.boost_root, 'status' ) )
        utils.system( [ test_cmd ] )
        os.chdir( cd )

    def command_test_boost_build(self):
        if self.libraries is not None and "build" not in self.libraries:
            return

        self.log( 'Running Boost.Build tests' )
        # Find the true names of the toolsets used for testing
        toolsets = os.listdir(os.path.join(self.regression_results,
                                           "boost/bin.v2/libs/any/test/any_test.test"));
        for t in toolsets:
            d = os.path.join(self.regression_results, ("boost-build-%s" % (t)))
            utils.makedirs (d)
            fn = os.path.join(d, "test_log.xml")
            cd = os.getcwd()
            try:
                os.chdir (os.path.join (self.boost_root, 'tools/build/test'))
                bjam_path = os.path.dirname (self.tool_path( self.bjam ))
                self.log( "Using bjam binary in '%s'" % (bjam_path))
                os.putenv('PATH', bjam_path + os.pathsep + os.environ['PATH'])
                utils.system ( [ '"%s" test_all.py --default-bjam --xml %s > %s' % (sys.executable, t, fn) ] )
            finally:
                os.chdir( cd )

    def command_test_process(self):
        self.log( 'Getting test case results out of "%s"...' % self.regression_log )
        cd = os.getcwd()
        os.chdir( os.path.join( self.boost_root, 'status' ) )
        utils.checked_system( [
            '"%s" %s --locate-root "%s" --input-file "%s"' % (
                self.tool_path(self.process_jam_log),
                '--echo' if self.verbose_log_processing else '',
                self.regression_results,
                self.regression_log )
            ] )
        os.chdir( cd )

    def command_collect_logs(self):
        comment_path = os.path.join( self.regression_root, self.comment )
        if not os.path.exists( comment_path ):
            self.log( 'Comment file "%s" not found; creating default comment.' % comment_path )
            f = open( comment_path, 'w' )
            f.write( '<p>Tests are run on %s platform.</p>' % self.platform_name() )
            f.close()

        source = 'tarball'
        revision = self.git_revision(self.boost_root)

        # Generate expanded comment file that has extra status
        # information. In particular the revisions of all the git
        # repos in the test tree.
        base_comment_path = comment_path
        comment_path = os.path.join(
            os.path.dirname(base_comment_path),
            'full-'+os.path.basename(base_comment_path))
        comment_file = open(comment_path, 'w')
        try:
            comment_file.write("\n")
            base_comment_file = open(base_comment_path, 'r')
            try:
                comment_file.write(base_comment_file.read())
            finally:
                base_comment_file.close()
            comment_file.write("<hr>\n")
            comment_file.write("<table><tr><th>Repo</th><th>Revision</th></tr>\n")
            for dir_root, dir_names, file_names in os.walk( self.regression_root ):
                for dir_name in dir_names:
                    if dir_name == '.git':
                        repo_dir = dir_root.replace(self.regression_root, '')
                        repo_revision = self.git_revision(dir_root)
                        comment_file.write(
                            "<tr><td><pre>%s</pre></td><td><pre>%s</pre></td></tr>\n"
                            %(repo_dir, repo_revision))
                for file_name in file_names:
                    if file_name == '.git':
                        repo_dir = dir_root.replace(self.regression_root, '')
                        repo_revision = self.git_revision(dir_root)
                        comment_file.write(
                            "<tr><td><pre>%s</pre></td><td><pre>%s</pre></td></tr>\n"
                            %(repo_dir, repo_revision))
            comment_file.write("</table>\n")
        finally:
            comment_file.close()

        if self.pjl_toolset != 'python':
            from collect_and_upload_logs import collect_logs
            if self.incremental:
                run_type = 'incremental'
            else:
                run_type = 'full'
            collect_logs(
                self.regression_results,
                self.runner, self.tag, self.platform, comment_path,
                self.timestamp_path,
                "",
                source, run_type,
                self.dart_server, self.proxy,
                revision )
        else:
            from process_jam_log import BJamLog2Results
            if self.incremental:
                run_type = '--incremental'
            else:
                run_type = ''
            BJamLog2Results([
                '--output='+os.path.join(self.regression_results,self.runner+'.xml'),
                '--runner='+self.runner,
                '--comment='+comment_path,
                '--tag='+self.tag,
                '--platform='+self.platform,
                '--source='+source,
                '--revision='+revision,
                run_type,
                self.regression_log
                ])
            self.compress_file(
                os.path.join(self.regression_results,self.runner+'.xml'),
                os.path.join(self.regression_results,self.runner+'.zip')
                )

    def command_upload_logs(self):
        from collect_and_upload_logs import upload_logs
        if self.ftp:
            self.retry(
                lambda:
                    upload_logs(
                        self.regression_results,
                        self.runner, self.group,
                        "",
                        self.ftp_proxy,
                        self.debug_level, self.send_bjam_log,
                        self.timestamp_path,
                        self.dart_server,
                        ftp_url = self.ftp )
                )
        else:
            self.retry(
                lambda:
                    upload_logs(
                        self.regression_results,
                        self.runner, self.group,
                        "",
                        self.ftp_proxy,
                        self.debug_level, self.send_bjam_log,
                        self.timestamp_path,
                        self.dart_server )
                )

    def command_regression(self):
        import socket
        try:
            mail_subject = 'Boost regression for %s on %s' % ( self.tag,
                socket.gethostname().split('.')[0] )
            start_time = time.localtime()
            if self.mail:
                self.log( 'Sending start notification to "%s"' % self.mail )
                self.send_mail(
                    '%s started at %s.' % ( mail_subject, format_time( start_time ) )
                    )

            self.command_get_tools()

            if self.local is not None:
                self.log( 'Using local file "%s"' % self.local )
                b = os.path.basename( self.local )
                tag = b[ 0: b.find( '.' ) ]
                self.log( 'Tag: "%s"' % tag  )
                self.unpack_tarball( self.local, self.boost_root )

            elif self.have_source:
                if not self.incremental: self.command_cleanup( 'bin' )

            else:
                if self.incremental or self.force_update:
                    if not self.incremental: self.command_cleanup( 'bin' )
                else:
                    self.command_cleanup()
                self.command_get_source()

            self.command_setup()

            # Not specifying --toolset in command line is not enough
            # that would mean to use Boost.Build default ones
            # We can skip test only we were explictly
            # told to have no toolsets in command line "--toolset="
            if self.toolsets != '': # --toolset=,
                if not self.skip_tests:
                    self.command_test()
                self.command_collect_logs()
                self.command_upload_logs()

            if self.mail:
                self.log( 'Sending report to "%s"' % self.mail )
                end_time = time.localtime()
                self.send_mail(
                    '%s completed successfully at %s.' % ( mail_subject, format_time( end_time ) )
                    )
        except:
            if self.mail:
                self.log( 'Sending report to "%s"' % self.mail )
                traceback_ = '\n'.join( apply( traceback.format_exception, sys.exc_info() ) )
                end_time = time.localtime()
                self.send_mail(
                    '%s failed at %s.' % ( mail_subject, format_time( end_time ) ),
                    traceback_ )
            raise

    def command_show_revision(self):
        modified = '$Date: 2013-02-28 12:09:13 -0600 (Thu, 28 Feb 2013) $'
        revision = '$Revision: 83205 $'

        import re
        re_keyword_value = re.compile( r'^\$\w+:\s+(.*)\s+\$$' )
        print('\n\tRevision: %s' % re_keyword_value.match( revision ).group( 1 ))
        print('\tLast modified on: %s\n' % re_keyword_value.match( modified ).group( 1 ))

    #~ Utilities...

    def main(self):
        for action in self.actions:
            action_m = "command_"+action.replace('-','_')
            if hasattr(self,action_m):
                getattr(self,action_m)()

    def platform_name(self):
        # See http://article.gmane.org/gmane.comp.lib.boost.testing/933
        if sys.platform == 'win32':
            return 'Windows'
        elif sys.platform == 'cygwin':
            return 'Windows/Cygwin'
        return platform.system()

    def log(self,message):
        sys.stdout.flush()
        sys.stderr.flush()
        sys.stderr.write( '# %s\n' % message )
        sys.stderr.flush()

    def rmtree(self,path):
        if os.path.exists( path ):
            import shutil
            #~ shutil.rmtree( unicode( path ) )
            if sys.platform == 'win32':
                os.system( 'del /f /s /q "%s" >nul 2>&1' % path )
                shutil.rmtree( unicode( path ) )
            else:
                os.system( 'rm -f -r "%s"' % path )

    def refresh_timestamp( self ):
        if os.path.exists( self.timestamp_path ):
           os.unlink( self.timestamp_path )
        open( self.timestamp_path, 'w' ).close()

    def timestamp( self ):
        return time.strftime(
            '%Y-%m-%dT%H:%M:%SZ',
            time.gmtime( os.stat( self.timestamp_path ).st_mtime ) )

    def retry( self, f, max_attempts=5, sleep_secs=10 ):
        for attempts in range( max_attempts, -1, -1 ):
            try:
                return f()
            except Exception as msg:
                self.log( '%s failed with message "%s"' % ( f.__name__, msg ) )
                if attempts == 0:
                    self.log( 'Giving up.' )
                    raise

                self.log( 'Retrying (%d more attempts).' % attempts )
                time.sleep( sleep_secs )

    def http_get( self, source_url, destination_file ):
        import urllib

        proxies = None
        if hasattr(self,'proxy') and self.proxy is not None:
            proxies = { 'https' : self.proxy }

        src = urllib.urlopen( source_url, proxies = proxies )

        f = open( destination_file, 'wb' )
        while True:
            data = src.read( 16*1024 )
            if len( data ) == 0: break
            f.write( data )

        f.close()
        src.close()

    def build_if_needed( self, tool, toolset ):
        if os.path.exists( tool[ 'path' ] ):
            self.log( 'Found preinstalled "%s"; will use it.' % tool[ 'path' ] )
            return

        self.log( 'Preinstalled "%s" not found; building one...' % tool[ 'path' ] )

        if toolset is None:
            if self.toolsets is not None:
                toolset = self.toolsets.split(',' )[0]
            else:
                toolset = tool[ 'default_toolset' ]
                self.log( 'Warning: No bootstrap toolset for "%s" was specified.' % tool[ 'name' ] )
                self.log( '         Using default toolset for the platform (%s).' % toolset )

        if os.path.exists( tool[ 'source_dir' ] ):
            self.log( 'Found "%s" source directory "%s"' % ( tool[ 'name' ], tool[ 'source_dir' ] ) )
            build_cmd = tool[ 'build_cmd' ]( toolset, tool['build_args'] )
            self.log( 'Building "%s" (%s)...' % ( tool[ 'name'], build_cmd ) )
            utils.system( [ 'cd "%s"' % tool[ 'source_dir' ], build_cmd ] )
        else:
            raise 'Could not find "%s" source directory "%s"' % ( tool[ 'name' ], tool[ 'source_dir' ] )

        if not 'build_path' in tool:
            tool[ 'build_path' ] = self.tool_path( tool )

        if not os.path.exists( tool[ 'build_path' ] ):
            raise 'Failed to find "%s" after build.' % tool[ 'build_path' ]

        self.log( '%s succesfully built in "%s" location' % ( tool[ 'name' ], tool[ 'build_path' ] ) )

    def tool_path( self, name_or_spec ):
        # Python 2 and 3 compatible
        try:
            basestring
        except NameError:
            basestring = str

        if isinstance( name_or_spec, basestring ):
            return os.path.join( self.regression_root, name_or_spec )

        if os.path.exists( name_or_spec[ 'path' ] ):
            return name_or_spec[ 'path' ]

        if 'build_path' in name_or_spec:
            return name_or_spec[ 'build_path' ]

        build_dir = name_or_spec[ 'build_dir' ]
        self.log( 'Searching for "%s" in "%s"...' % ( name_or_spec[ 'name' ], build_dir ) )
        for root, dirs, files in os.walk( build_dir ):
            if name_or_spec[ 'name' ] in files:
                return os.path.join( root, name_or_spec[ 'name' ] )

        raise Exception( 'Cannot find "%s" in any of the following locations:\n%s' % (
              name_or_spec[ 'name' ]
            , '\n'.join( [ name_or_spec[ 'path' ], build_dir ] )
            ) )

    def bjam_build_cmd( self, *rest ):
        if sys.platform == 'win32':
            cmd = 'build.bat %s' % self.bjam_toolset
        else:
            cmd = './build.sh %s' % self.bjam_toolset
        env_setup_key = 'BJAM_ENVIRONMENT_SETUP'
        if os.environ.has_key( env_setup_key ):
            return '%s & %s' % ( os.environ[env_setup_key], cmd )
        return cmd

    def bjam_cmd( self, toolsets, args = '', *rest ):
        build_path = self.regression_root
        if build_path[-1] == '\\': build_path += '\\'

        if self.timeout > 0:
            args += ' -l%s' % (self.timeout*60)

        cmd = '"%(bjam)s"' +\
            ' "-sBOOST_BUILD_PATH=%(bbpath)s"' +\
            ' "-sBOOST_ROOT=%(boost)s"' +\
            ' "--boost=%(boost)s"' +\
            ' "--boost-root=%(boost)s"' +\
            ' "--boost-build=%(bb)s"' +\
            ' "--debug-configuration"' +\
            ' %(arg)s'
        cmd %= {
            'bjam' : self.tool_path( self.bjam ),
            'bbpath' : os.pathsep.join([build_path,self.tools_bb_root]),
            'bb' : self.tools_bb_root,
            'boost' : self.boost_root,
            'arg' : args }

        if toolsets:
            for toolset in toolsets.split( ',' ):
                cmd += ' toolset=' + toolset

        return cmd

    def send_mail( self, subject, msg = '' ):
        import smtplib
        if not self.smtp_login:
            server_name = 'mail.%s' % mail.split( '@' )[-1]
            user_name = None
            password = None
        else:
            server_name = self.smtp_login.split( '@' )[-1]
            ( user_name, password ) = self.smtp_login.split( '@' )[0].split(':')

        log( '    Sending mail through "%s"...' % server_name )
        smtp_server = smtplib.SMTP( server_name )
        smtp_server.set_debuglevel( self.debug_level )
        if user_name:
            smtp_server.login( user_name, password )

        smtp_server.sendmail( self.mail, [ self.mail ],
            'Subject: %s\nTo: %s\n\n%s' % ( subject, self.mail, msg ) )

    def compress_file( self, file_path, archive_path ):
        utils.log( 'Compressing "%s"...' % file_path )

        try:
            import zipfile
            z = zipfile.ZipFile( archive_path, 'w', zipfile.ZIP_DEFLATED )
            z.write( file_path, os.path.basename( file_path ) )
            z.close()
            utils.log( 'Done writing "%s".'% archive_path )
        except Exception as msg:
            utils.log( 'Warning: Compressing falied (%s)' % msg )
            utils.log( '         Trying to compress using a platform-specific tool...' )
            try:
                import zip_cmd
            except ImportError:
                script_dir = os.path.dirname( os.path.abspath( sys.argv[0] ) )
                utils.log( 'Could not find \'zip_cmd\' module in the script directory (%s).' % script_dir )
                raise Exception( 'Compressing failed!' )
            else:
                if os.path.exists( archive_path ):
                    os.unlink( archive_path )
                    utils.log( 'Removing stale "%s".' % archive_path )

                zip_cmd.main( file_path, archive_path )
                utils.log( 'Done compressing "%s".' % archive_path )

    #~ Downloading source, from GIT...

    def git_command(self, command, *args):
        git_cli = "git %(command)s" % { 'command': command }
        for a in args:
            git_cli += " \""+a+"\""
        self.log( 'Executing GIT command: %s> %s' % (os.getcwd(), git_cli) )
        rc = os.system( git_cli )
        if rc != 0:
            raise Exception( 'GIT command "%s" failed with code %d' % (git_cli, rc) )
        return rc

    def git_checkout(self, info, branch, clean = False):
        git_root = os.path.join(self.regression_root, info['dir'])
        if self.use_dulwich:
            import git;
            g = git.RemoteRepo(git_root, info['git'], branch=branch, reset=False)
            g.checkout()
        else:
            if os.path.exists( os.path.join(git_root, ".git") ):
                os.chdir( git_root )
                self.git_command( 'submodule foreach', 'git submodule deinit .')
                self.git_command( 'remote', 'set-branches', '--add', 'origin',
                    branch)
                self.git_command( 'pull', '--recurse-submodules' )
                self.git_command( 'checkout', branch)
                self.git_command( 'submodule', 'update', '--init' )
                if clean:
                    self.git_command( 'submodule foreach', 'git reset --quiet --hard ; git clean -fxd')
                    self.git_command( 'reset', '--hard' )
                    self.git_command( 'clean', '-fxd')
                    # self.git_command( 'status' )
            else:
                self.git_command(
                    'init',
                    git_root)
                os.chdir( git_root )
                self.git_command(
                    'remote', 'add', '--no-tags', '-t', branch, 'origin',
                    info[ 'git' ] )
                self.git_command(
                    'fetch', '--depth=1' )
                self.git_command(
                    'checkout', branch )
                self.git_command(
                    'submodule', 'update', '--init' )
        os.chdir( self.regression_root )

    def git_source_checkout(self, clean = False):
        os.chdir( self.regression_root )
        self.git_checkout(git_info['boost'], self.git_branch(), clean)

    def git_branch(self):
        if self.tag in git_branch:
            return git_branch[self.tag]
        else:
            return self.tag

    def git_revision(self, root):
        result = ''
        if self.use_git:
            dot_git = os.path.join(root, '.git')
            if os.path.isfile(dot_git):
                f = open(dot_git, 'r')
                try:
                    subref = f.read().strip().rpartition(' ')[2]
                    git_rev_file = os.path.join(
                        root, subref, 'HEAD')
                finally:
                    f.close()
            else:
                f = open(os.path.join(dot_git, 'HEAD'), 'r')
                try:
                    git_head_info = f.read().strip().rpartition(' ')[2]
                    git_rev_file = os.path.join(dot_git, git_head_info)
                finally:
                    f.close()
            f = open( git_rev_file, 'r' )
            try:
                result = f.read().strip()
            finally:
                f.close()
        return result

    #~ Downloading and extracting source archives, from tarballs or zipballs...

    def get_tarball( self, *args ):
        if not args or args == []:
            args = [ 'download', 'unpack' ]

        tarball_path = None

        if hasattr(self,'local') and self.local is not None:
            tarball_path = self.local
        elif 'download' in args:
            tarball_path = self.download_tarball(self.boost_tarball_name(),self.boost_tarball_url())
        if not tarball_path:
            tarball_path = os.path.join( self.regression_root, self.boost_tarball_url() )

        if 'unpack' in args:
            self.unpack_tarball( tarball_path, self.boost_root )
        pass

    def download_tarball( self, tarball_name, tarball_url ):
        tarball_path = os.path.join( self.regression_root, tarball_name )

        self.log( 'Downloading "%s" to "%s"...'  % ( tarball_url, os.path.dirname( tarball_path ) ) )

        if os.path.exists( tarball_path ):
            os.unlink( tarball_path )
        self.http_get( tarball_url, tarball_path )

        return tarball_path

    def tarball_url( self, path ):
        return 'http://beta.boost.org/development/snapshot.php/%s' % path

    def boost_tarball_name( self ):
        return 'boost-%s.tar.bz2' % self.tag.split( '/' )[-1]

    def boost_tarball_url( self ):
        return self.tarball_url( self.tag )

    def unpack_tarball( self, tarball_path, target_path ):
        self.log( 'Looking for old unpacked archives...' )
        old_boost_dirs = self.find_boost_dirs( )

        for old_boost_dir in old_boost_dirs:
            if old_boost_dir != tarball_path:
                self.log( 'Deleting old directory %s.' % old_boost_dir )
                self.rmtree( old_boost_dir )

        self.log( 'Unpacking boost tarball ("%s")...' % tarball_path )

        tarball_name = os.path.basename( tarball_path )
        extension = tarball_name[ tarball_name.find( '.' ) : ]

        if extension in ( ".tar.gz", ".tar.bz2" ):
            import tarfile
            import stat

            mode = os.path.splitext( extension )[1][1:]
            tar = tarfile.open( tarball_path, 'r:%s' % mode )
            for tarinfo in tar:
                tar.extract( tarinfo, self.regression_root )
                if sys.platform == 'win32' and not tarinfo.isdir():
                    # workaround what appears to be a Win32-specific bug in 'tarfile'
                    # (modification times for extracted files are not set properly)
                    f = os.path.join( self.regression_root, tarinfo.name )
                    os.chmod( f, stat.S_IWRITE )
                    os.utime( f, ( tarinfo.mtime, tarinfo.mtime ) )
            tar.close()
        elif extension in ( ".zip" ):
            import zipfile

            z = zipfile.ZipFile( tarball_path, 'r', zipfile.ZIP_DEFLATED )
            for f in z.infolist():
                destination_file_path = os.path.join( self.regression_root, f.filename )
                if destination_file_path[-1] == "/": # directory
                    if not os.path.exists( destination_file_path  ):
                        os.makedirs( destination_file_path  )
                else: # file
                    result = open( destination_file_path, 'wb' )
                    result.write( z.read( f.filename ) )
                    result.close()
            z.close()
        else:
            raise 'Do not know how to unpack archives with extension \"%s\"' % extension

        boost_dir = self.find_boost_dirs()[0]
        self.log( '    Unpacked into directory "%s"' % boost_dir )

        if os.path.exists( target_path ):
            self.log( 'Deleting "%s" directory...' % target_path )
            self.rmtree( target_path )

        self.log( 'Renaming "%s" into "%s"' % ( boost_dir, target_path ) )
        os.rename( boost_dir, target_path )

    def find_boost_dirs( self ):
        return [
            x for x in
                glob.glob( os.path.join( self.regression_root, 'boost[-_]*' ) )
                if os.path.isdir( x )
            ]
