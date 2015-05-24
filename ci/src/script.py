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
import string
import sys
import time

apt_info = {
    'clang-3.4' : {
        'bin' : 'clang-3.4',
        'ppa' : ["ppa:h-rayflood/llvm"],
        'package' : 'clang-3.4',
        'debugpackage' : 'libstdc++6-4.6-dbg'
        },
    'clang-3.5' : {
        'bin' : 'clang-3.5',
        'ppa' : ["ppa:h-rayflood/llvm-upper", "ppa:h-rayflood/gcc-upper"],
        'package' : 'clang-3.5',
        'debugpackage' : 'libstdc++6-4.6-dbg'
        },
    'gcc-4.7' : {
        'bin' : 'gcc-4.7',
        'ppa' : ["ppa:ubuntu-toolchain-r/test"],
        'package' : 'g++-4.7',
        'debugpackage' : 'libstdc++6-4.8-dbg'
        },
    'gcc-4.8' : {
        'bin' : 'gcc-4.8',
        'ppa' : ["ppa:ubuntu-toolchain-r/test"],
        'package' : 'g++-4.8',
        'debugpackage' : 'libstdc++6-4.8-dbg'
        },
    'gcc-4.9' : {
        'bin' : 'gcc-4.9',
        'ppa' : ["ppa:ubuntu-toolchain-r/test"],
        'package' : 'g++-4.9',
        'debugpackage' : 'libstdc++6-4.8-dbg'
        },
    }

class utils:
    
    @staticmethod
    def system( commands ):
        if sys.platform == 'win32':
            utils.log('\n'.join(commands))
            f = open( 'tmp.cmd', 'w' )
            f.write( string.join( commands, '\n' ) )
            f.close()
            rc = os.system( 'tmp.cmd' )
            return rc
        else:
            utils.log(' && '.join(commands))
            rc = os.system( ' && '.join( commands ) )
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
        sys.stdout.flush()
        sys.stderr.flush()
        sys.stderr.write( '# ' + '    ' * utils.log_level() +  message + '\n' )
        sys.stderr.flush()

    @staticmethod
    def rmtree(path):
        if os.path.exists( path ):
            import shutil
            #~ shutil.rmtree( unicode( path ) )
            if sys.platform == 'win32':
                os.system( 'del /f /s /q "%s" >nul 2>&1' % path )
                shutil.rmtree( unicode( path ) )
            else:
                os.system( 'rm -f -r "%s"' % path )

    @staticmethod
    def retry( f, max_attempts=5, sleep_secs=10 ):
        for attempts in range( max_attempts, -1, -1 ):
            try:
                return f()
            except Exception, msg:
                utils.log( '%s failed with message "%s"' % ( f.__name__, msg ) )
                if attempts == 0:
                    utils.log( 'Giving up.' )
                    raise

                utils.log( 'Retrying (%d more attempts).' % attempts )
                time.sleep( sleep_secs )

    @staticmethod
    def web_get( source_url, destination_file, proxy = None ):
        import urllib

        proxies = None
        if proxy is not None:
            proxies = {
                'https' : proxy,
                'http' : proxy
                }

        src = urllib.urlopen( source_url, proxies = proxies )

        f = open( destination_file, 'wb' )
        while True:
            data = src.read( 16*1024 )
            if len( data ) == 0: break
            f.write( data )

        f.close()
        src.close()

    @staticmethod
    def unpack_archive( archive_path ):
        utils.log( 'Unpacking archive ("%s")...' % archive_path )

        archive_name = os.path.basename( archive_path )
        extension = archive_name[ archive_name.find( '.' ) : ]

        if extension in ( ".tar.gz", ".tar.bz2" ):
            import tarfile
            import stat

            mode = os.path.splitext( extension )[1][1:]
            tar = tarfile.open( archive_path, 'r:%s' % mode )
            for tarinfo in tar:
                tar.extract( tarinfo )
                if sys.platform == 'win32' and not tarinfo.isdir():
                    # workaround what appears to be a Win32-specific bug in 'tarfile'
                    # (modification times for extracted files are not set properly)
                    f = os.path.join( os.curdir, tarinfo.name )
                    os.chmod( f, stat.S_IWRITE )
                    os.utime( f, ( tarinfo.mtime, tarinfo.mtime ) )
            tar.close()
        elif extension in ( ".zip" ):
            import zipfile

            z = zipfile.ZipFile( archive_path, 'r', zipfile.ZIP_DEFLATED )
            for f in z.infolist():
                destination_file_path = os.path.join( os.curdir, f.filename )
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

class script:

    def __init__(self):
        commands = map(
            lambda m: m[8:].replace('_','-'),
            filter(
                lambda m: m.startswith('command_'),
                script.__dict__.keys())
            )
        commands.sort()
        commands = "commands: %s" % ', '.join(commands)

        opt = optparse.OptionParser(
            usage="%prog [options] [commands]",
            description=commands)

        #~ Base Options:
        opt.add_option( '--toolset',
            help="single toolset to test with" )

        #~ Debug Options:
        opt.add_option( '--debug-level',
            help="debugging level; controls the amount of debugging output printed",
            type='int' )

        #~ Defaults
        self.toolset=os.getenv("TOOLSET")
        self.debug_level=0
        ( _opt_, self.actions ) = opt.parse_args(None,self)
        if not self.actions or self.actions == []:
            self.actions = [ 'info' ]
        
        if sys.platform == 'win32':
            self.b2 = { 'name' : 'b2.exe' }
        elif sys.platform == 'cygwin':
            self.b2 = { 'name' : 'b2.exe' }
        else:
            self.b2 = { 'name' : 'b2' }
        self.travis_build_dir = os.getenv("TRAVIS_BUILD_DIR")

        self.main()

    #~ The various commands that make up the testing sequence...

    def command_info(self):
        pass

    def command_travis_before_install(self):
        pass

    def command_travis_install(self):
        # Fetch & install toolset..
        os.chdir(self.travis_build_dir)
        if self.toolset:
            self.travis_install_toolset(self.toolset)
        # Fetch & install BBv2..
        os.chdir(self.travis_build_dir)
        utils.retry(
            lambda:
                utils.web_get(
                    "https://github.com/boostorg/build/archive/develop.tar.gz",
                    "boost_bb.tar.gz")
            )
        utils.unpack_archive("boost_bb.targ.gz")
        os.chdir(os.path.join(self.travis_build_dir, "build-develop"))
        utils.checked_system(["./bootstrap.sh"])
        utils.checked_system(["./b2 install --prefix=/usr"])
        #
        os.chdir(self.travis_build_dir)

    def command_travis_before_script(self):
        os.chdir(self.travis_build_dir)
        # echo "project ROOT : : : build-dir bin ;" > jamroot.jam
        os.chdir(self.travis_build_dir)

    def command_travis_script(self):
        os.chdir(os.path.join(self.travis_build_dir, "test"))
        utils.checked_system([
            self.b2_cmd(self.toolset, "-a --verbose-test")
            ])

    def command_travis_after_success(self):
        pass

    def command_travis_after_failure(self):
        pass

    def command_travis_after_script(self):
        pass

    #~ Utilities...

    def main(self):
        for action in self.actions:
            action_m = "command_"+action.replace('-','_')
            if hasattr(self,action_m):
                getattr(self,action_m)()

    def b2_cmd( self, toolset, args = '', *rest ):
        cmd = '"%(b2)s"' +\
            ' "--debug-configuration"' +\
            ' %(arg)s'
        cmd %= {
            'b2' : self.b2,
            'arg' : args }

        if toolset:
            import string
            cmd += ' toolset=' + toolset

        return cmd
    
    def travis_install_toolset(self, toolset):
        info = apt_info[toolset]
        for ppa in info['ppa']:
            utils.checked_system([
                'sudo add-apt-repository --yes %s'%(ppa)])
        utils.checked_system([
            'sudo apt-get update -qq'])
        utils.checked_system([
            'sudo apt-get install -qq %s %s'%(info['package'], info['debugpackage'])])

script()