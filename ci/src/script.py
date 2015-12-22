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
import subprocess
import codecs
import inspect

toolset_info = {
    'clang-3.4' : {
        'ppa' : ["ppa:h-rayflood/llvm"],
        'package' : 'clang-3.4',
        'debugpackage' : 'libstdc++6-4.6-dbg',
        'command' : 'clang++-3.4',
        'toolset' : 'clang',
        'version' : ''
        },
    'clang-3.5' : {
        'ppa' : ["ppa:h-rayflood/llvm-upper", "ppa:h-rayflood/gcc-upper"],
        'package' : 'clang-3.5',
        'debugpackage' : 'libstdc++6-4.6-dbg',
        'command' : 'clang++-3.5',
        'toolset' : 'clang',
        'version' : ''
        },
    'clang-3.6' : {
        'ppa' : ["ppa:h-rayflood/llvm-upper", "ppa:h-rayflood/gcc-upper"],
        'package' : 'clang-3.6',
        'debugpackage' : 'libstdc++6-4.6-dbg',
        'command' : 'clang++-3.6',
        'toolset' : 'clang',
        'version' : ''
        },
    'gcc-4.7' : {
        'ppa' : ["ppa:ubuntu-toolchain-r/test"],
        'package' : 'g++-4.7',
        'debugpackage' : 'libstdc++6-4.8-dbg',
        'command' : 'g++-4.7',
        'toolset' : 'gcc',
        'version' : ''
        },
    'gcc-4.8' : {
        'bin' : 'gcc-4.8',
        'ppa' : ["ppa:ubuntu-toolchain-r/test"],
        'package' : 'g++-4.8',
        'debugpackage' : 'libstdc++6-4.8-dbg',
        'command' : 'g++-4.8',
        'toolset' : 'gcc',
        'version' : ''
        },
    'gcc-4.9' : {
        'ppa' : ["ppa:ubuntu-toolchain-r/test"],
        'package' : 'g++-4.9',
        'debugpackage' : 'libstdc++6-4.8-dbg',
        'command' : 'g++-4.9',
        'toolset' : 'gcc',
        'version' : ''
        },
    'gcc-5.1' : {
        'ppa' : ["ppa:ubuntu-toolchain-r/test"],
        'package' : 'g++-5',
        'debugpackage' : 'libstdc++6-4.8-dbg',
        'command' : 'g++-5',
        'toolset' : 'gcc',
        'version' : ''
        },
    'vs-2008' : {
        'toolset' : 'msvc',
        'command' : '',
        'version' : '9.0'
        },
    'vs-2010' : {
        'toolset' : 'msvc',
        'command' : '',
        'version' : '10.0'
        },
    'vs-2012' : {
        'toolset' : 'msvc',
        'command' : '',
        'version' : '11.0'
        },
    'vs-2013' : {
        'toolset' : 'msvc',
        'command' : '',
        'version' : '12.0'
        },
    'vs-2015' : {
        'toolset' : 'msvc',
        'command' : '',
        'version' : '14.0'
        },
    'xcode-6.1' : {
        'command' : 'clang++',
        'toolset' : 'clang',
        'version' : ''
        },
    'xcode-6.2' : {
        'command' : 'clang++',
        'toolset' : 'clang',
        'version' : ''
        },
    'xcode-6.3' : {
        'command' : 'clang++',
        'toolset' : 'clang',
        'version' : ''
        },
    'xcode-6.4' : {
        'command' : 'clang++',
        'toolset' : 'clang',
        'version' : ''
        },
    'xcode-7.0' : {
        'command' : 'clang++',
        'toolset' : 'clang',
        'version' : ''
        },
    'xcode-7.1' : {
        'command' : 'clang++',
        'toolset' : 'clang',
        'version' : ''
        },
    'xcode-7.2' : {
        'command' : 'clang++',
        'toolset' : 'clang',
        'version' : ''
        },
    }

class SystemCallError(Exception):
    def __init__(self, command, result):
        self.command = command
        self.result = result
    def __str__(self, *args, **kwargs):
        return "'%s' ==> %s"%("' '".join(self.command), self.result)

class utils:
    
    @staticmethod
    def call(*command):
        utils.log( "%s> '%s'"%(os.getcwd(), "' '".join(command)) )
        result = subprocess.call(command)
        if result != 0:
            print "Failed: '%s' ERROR = %s"%("' '".join(command), result)
        return result
    
    @staticmethod
    def check_call(*command):
        result = utils.call(*command)
        if result != 0:
            raise(SystemCallError(command, result))
    
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
    
    @staticmethod
    def make_file(filename, *text):
        f = codecs.open( filename, 'w', 'utf-8' )
        f.write( string.join( text, '\n' ) )
        f.close()

class script:

    def __init__(self, build_dir = None, test_args = []):
        commands = [];
        for method in inspect.getmembers(self, predicate=inspect.ismethod):
            if method[0].startswith('command_'):
                commands.append(method[0][8:].replace('_','-'))
        commands = "commands: %s" % ', '.join(commands)

        opt = optparse.OptionParser(
            usage="%prog [options] [commands]",
            description=commands)

        #~ Base Options:
        opt.add_option( '--toolset',
            help="single toolset to test with" )
        opt.add_option( '--target',
            help="test target to build for testing, defaults to TARGET or 'minimal'")

        #~ Debug Options:
        opt.add_option( '--debug-level',
            help="debugging level; controls the amount of debugging output printed",
            type='int' )

        #~ Defaults
        self.test_args = test_args
        self.toolset=os.getenv("TOOLSET")
        if not self.toolset:
            # Travis-CI likes injecting a default, unspecified, run
            # in the mix of testing. So we avoid doing anything in
            # that case. And let them waste their resources as long
            # as they don't want to fix their own bug.
            return
        self.target=os.getenv('TARGET', 'minimal')
        self.debug_level=0
        ( _opt_, self.actions ) = opt.parse_args(None,self)
        if not self.actions or self.actions == []:
            self.actions = [ 'info' ]
        
        if sys.platform == 'win32':
            self.b2 = { 'name' : 'C:\\boost-build\\bin\\b2.exe' }
        elif sys.platform == 'cygwin':
            self.b2 = { 'name' : 'b2.exe' }
        else:
            self.b2 = { 'name' : 'b2' }
        self.build_dir = build_dir
        if self.build_dir:
            self.root_dir = os.path.dirname(self.build_dir)
        else:
            self.build_dir = os.getcwd()
            self.root_dir = os.getcwd()

        self.main()

    # Common test commands in the order they should be executed..
    
    def command_base_info(self):
        pass
    
    def command_base_install(self):
        # Fetch & install BBv2..
        os.chdir(self.root_dir)
        utils.retry(
            lambda:
                utils.web_get(
                    "https://github.com/boostorg/build/archive/develop.tar.gz",
                    "boost_bb.tar.gz")
            )
        utils.unpack_archive("boost_bb.tar.gz")
        os.chdir(os.path.join(self.root_dir, "build-develop"))
        if sys.platform == 'win32':
            utils.check_call('cmd.exe', '/C', os.path.join(self.root_dir, "build-develop", "bootstrap.bat"))
            utils.check_call("b2","install", "-d0")
        else:
            utils.check_call("./bootstrap.sh")
            utils.check_call("sudo","./b2","install", "-d0")
        #
        os.chdir(self.build_dir)

    def command_base_before_test(self):
        # Create jamroot project file as it's not present
        # in individual libraries.
        os.chdir(self.root_dir)
        utils.make_file(os.path.join(self.root_dir, 'jamroot.jam'),
            "project ROOT : : : build-dir bin ;")
        # Create config file for toolset.
        utils.make_file(os.path.join(self.root_dir, 'project-config.jam'),
            "using %s : %s : %s ;"%(
                toolset_info[self.toolset]['toolset'],
                toolset_info[self.toolset]['version'],
                toolset_info[self.toolset]['command']))
        #
        os.chdir(self.build_dir)

    def command_base_test(self):
        os.chdir(os.path.join(self.build_dir, "test"))
        utils.check_call(
            *self.b2_cmd(
                toolset_info[self.toolset]['toolset'],
                "-a", "--verbose-test",
                self.target,
                *self.test_args)
            )

    #~ Utilities...

    def main(self):
        for action in self.actions:
            action_m = "command_"+action.replace('-','_')
            if hasattr(self,action_m):
                getattr(self,action_m)()

    def b2_cmd( self, toolset, *args ):
        cmd = [self.b2['name'],'--debug-configuration']
        cmd.extend(args)

        if toolset:
            import string
            cmd.append('toolset=' + toolset)

        return cmd

class script_travis(script):

    def __init__(self):
        travis_build_dir = os.getenv("TRAVIS_BUILD_DIR")
        script.__init__(self, build_dir=travis_build_dir)

    # Travis-CI commands in the order they are executed..
    
    def command_install(self):
        # Fetch & install toolset..
        os.chdir(self.root_dir)
        if self.toolset:
            self.travis_install_toolset(self.toolset)
        #
        self.command_base_install()

    def command_before_script(self):
        self.command_base_before_test()

    def command_script(self):
        self.command_base_test()

    def command_after_success(self):
        pass

    def command_after_failure(self):
        pass

    def command_after_script(self):
        pass
    
    # Installs specific toolset on Travis CI systems.
    def travis_install_toolset(self, toolset):
        info = toolset_info[toolset]
        if sys.platform.startswith('linux'):
            for ppa in info['ppa']:
                utils.check_call(
                    'sudo','add-apt-repository','--yes',ppa)
            utils.check_call(
                'sudo','apt-get','update','-qq')
            utils.check_call(
                'sudo','apt-get','install','-qq',info['package'],info['debugpackage'])

class script_appveyor(script):
    
    def __init__(self):
        appveyor_build_dir = os.getenv("APPVEYOR_BUILD_FOLDER")
        test_args = []
        if os.getenv("PLATFORM"):
            test_args.append("address-model=%s"%(os.getenv("PLATFORM")))
        if os.getenv("CONFIGURATION"):
            test_args.append("variant=%s"%(os.getenv("CONFIGURATION")))
        script.__init__(self,
            build_dir=appveyor_build_dir,
            test_args=test_args)
    
    # Appveyor commands in the order they are executed..
    
    def command_install(self):
        self.command_base_install()
    
    def command_before_build(self):
        pass
    
    def command_build_script(self):
        pass
    
    def command_after_build(self):
        pass
    
    def command_before_test(self):
        self.command_base_before_test()
    
    def command_test_script(self):
        self.command_base_test()
    
    def command_after_test(self):
        pass
    
    def command_on_success(self):
        pass
    
    def command_on_failure(self):
        pass
    
    def command_on_finish(self):
        pass

if os.getenv('APPVEYOR', False):
    script_appveyor()
elif os.getenv('TRAVIS', False):
    script_travis()
else:
    script()

