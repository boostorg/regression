#!/usr/bin/env python

# Copyright Rene Rivera 2007-2013
#
# Distributed under the Boost Software License, Version 1.0.
# (See accompanying file LICENSE_1_0.txt or copy at
# http://www.boost.org/LICENSE_1_0.txt)

import os
import os.path
import shutil
import sys
try:
    from urllib.request import FancyURLopener
except ImportError:
    from urllib import FancyURLopener

#~ Using --skip-script-download is useful to avoid repeated downloading of
#~ the regression scripts when doing the regression commands individually.
no_update_argument = "--skip-script-download"
no_update = no_update_argument in sys.argv
if no_update:
    del sys.argv[sys.argv.index(no_update_argument)]

use_local_argument = '--use-local'
use_local = use_local_argument in sys.argv
if use_local:
    del sys.argv[sys.argv.index(use_local_argument)]

#~ The directory this file is in.
if use_local:
    root = os.path.abspath(os.path.realpath(os.path.curdir))
else:
    root = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
print('# Running regressions in %s...' % root)

script_sources = [ 'collect_and_upload_logs.py', 'process_jam_log.py', 'regression.py' ]
script_local = root
if use_local:
    script_remote = 'file://'+os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
else:
    script_remote = 'https://raw.githubusercontent.com/boostorg/regression/develop/testing/src'
script_dir = os.path.join(root,'boost_regression_src')

if not no_update:
    #~ Bootstrap.
    #~ * Clear out any old versions of the scripts
    print('# Creating regression scripts at %s...' % script_dir)
    if os.path.exists(script_dir):
        shutil.rmtree(script_dir)
    os.mkdir(script_dir)
    #~ * Get new scripts, either from local working copy, or from remote
    if use_local and os.path.exists(script_local):
        print('# Copying regression scripts from %s...' % script_local)
        for src in script_sources:
            shutil.copyfile( os.path.join(script_local,src), os.path.join(script_dir,src) )
    else:
        print('# Downloading regression scripts from %s...' % script_remote)
        proxy = None
        for a in sys.argv[1:]:
            if a.startswith('--proxy='):
                proxy = {'https' : a.split('=')[1] }
                print('--- %s' %(proxy['https']))
                break
        for src in script_sources:
            FancyURLopener(proxy).retrieve(
                '%s/%s' % (script_remote,src), os.path.join(script_dir,src) )

#~ * Make the scripts available to Python
sys.path.insert(0,os.path.join(root,'boost_regression_src'))

#~ Launch runner.
from regression import runner
runner(root)
