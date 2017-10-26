#!/bin/sh

#~ Copyright Rene Rivera 2014-2015
#~ Distributed under the Boost Software License, Version 1.0.
#~ (See accompanying file LICENSE_1_0.txt or http://www.boost.org/LICENSE_1_0.txt)

set -e

REGRESSION_BRANCH=develop

log_time()
{
    echo `date` "::" $1
    echo `date` "::" $1 >> boost-reports-time.log
}

build_all()
{
    log_time "Start of testing. [build_all]"
    build_setup
    update_tools
    case "${CIRCLE_NODE_INDEX}" in
        0)
            build_one develop
            ;;
        1)
            build_one master
            ;;
        *)
            build_one develop
            build_one master
            ;;
    esac
    log_time "End of testing. [build_all]"
}

build_one()
{
    echo "Building results for branch: ${1}"
    build_results "${1}" 2>&1 | tee boost-reports/"${1}".log
    upload_results "${1}"
}

git_update()
{
    cwd=`pwd`
    if [ -d "${1}" ]; then
        cd "${1}"
        git remote set-branches --add origin "${2}"
        git pull --recurse-submodules
        git checkout "${2}"
    else
        mkdir -p "${1}"
        git init "${1}"
        cd "${1}"
        git remote add --no-tags -t "${2}" origin "${3}"
        git fetch
        git checkout "${2}"
    fi
    cd "${cwd}"
}

git_submodule_update()
{
    cwd=`pwd`
    cd "${1}"
    git submodule update --init "${2}"
    cd "${cwd}"
}

build_setup()
{
    log_time "Get tools. [build_setup]"
    cwd=`pwd`
    mkdir -p boost-reports/develop
    mkdir -p boost-reports/master
    log_time "Git; boost_root [build_setup]"
    git_update "${cwd}/boost-reports/boost_root" master 'https://github.com/boostorg/boost.git'
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/algorithm
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/any
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/array
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/assert
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/bind
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/concept_check
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/config
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/container
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/core
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/crc
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/date_time
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/detail
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/exception
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/filesystem
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/foreach
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/format
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/function
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/functional
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/integer
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/io
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/iostreams
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/iterator
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/lexical_cast
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/math
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/move
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/mpl
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/numeric/conversion
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/optional
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/predef
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/preprocessor
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/property_tree
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/program_options
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/range
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/regex
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/smart_ptr
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/static_assert
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/system
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/throw_exception
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/tokenizer
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/tuple
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/type_index
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/type_traits
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/unordered
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/utility
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/variant
    git_submodule_update "${cwd}/boost-reports/boost_root" libs/wave
    git_submodule_update "${cwd}/boost-reports/boost_root" tools/inspect
    log_time "Git; boost_regression [build_setup]"
    git_update "${cwd}/boost-reports/boost_regression" ${REGRESSION_BRANCH} 'https://github.com/boostorg/regression.git'
    log_time "Git; boost_bb [build_setup]"
    git_update "${cwd}/boost-reports/boost_bb" develop 'https://github.com/boostorg/build.git'
    cd "${cwd}"
}

update_tools()
{
    log_time "Build tools. [update_tools]"
    cwd=`pwd`
    cd "${cwd}/boost-reports/boost_bb"
    ./bootstrap.sh
    cd "${cwd}/boost-reports/boost_regression/reports/build"
    "${cwd}/boost-reports/boost_bb/b2" \
        "--boost-build=${cwd}/boost-reports/boost_bb/src" \
        "--boost-root=${cwd}/boost-reports/boost_root" install
    cd "${cwd}"
}

report_info()
{
cat - > comment.html <<HTML
<table style="border-spacing: 0.5em;">
    <tr>
        <td style="vertical-align: top;"><tt>uname</tt></td>
        <td>
            <pre style="border: 1px solid #666; overflow: auto;">
`uname -a`
            </pre>
        </td>
    </tr>
    <tr>
        <td style="vertical-align: top;"><tt>uptime</tt></td>
        <td>
            <pre style="border: 1px solid #666; overflow: auto;">
`uptime`
            </pre>
        </td>
    </tr>
    <tr>
        <td style="vertical-align: top;"><tt>python</tt></td>
        <td>
            <pre style="border: 1px solid #666; overflow: auto;">
`python --version 2>&1`
            </pre>
        </td>
    </tr>
    <tr>
        <td style="vertical-align: top;">current run</td>
        <td>
            <pre style="border: 1px solid #666; overflow: auto;">
`date -u`
            </pre>
        </td>
    </tr>
</table>
HTML
}

build_results()
{
    tag="${1?'error: command line missing branch-name argument'}"
    log_time "Build results for branch ${tag}. [build_results]"
    reports="dd,ds,i,n"
    cwd=`pwd`
    cd boost-reports
    cd "${1}"
    root=`pwd`
    boost=${cwd}/boost-reports/boost_root
    (cd ${boost} && git checkout origin/${1} -- status/explicit-failures-markup.xml)
    report_info
    python "${cwd}/boost-reports/boost_regression/reports/src/boost_wide_report.py" \
        --locate-root="${root}" \
        --tag=${tag} \
        --expected-results="${boost}/status/expected_results.xml" \
        --failures-markup="${boost}/status/explicit-failures-markup.xml" \
        --comment="comment.html" \
        --user="" \
        --reports=${reports} \
        "--boost-report=${cwd}/boost-reports/boost_regression/stage/bin/boost_report"
    cd "${cwd}"
}

upload_results()
{
    log_time "Upload results for branch $1. [upload_results]"
    cwd=`pwd`
    cd boost-reports
    upload_dir=/home/grafik/www.boost.org/testing
    
    mv ${1}/report.zip ${1}.zip
    upload_ext=.zip.${LOGNAME}
    mv ${1}.zip ${1}${upload_ext}
    rsync -vuz "--rsh=ssh -l grafik" --stats \
      ${1}${upload_ext} grafik@www.boost.org:/${upload_dir}/incoming/
    ssh grafik@www.boost.org \
      mv ${upload_dir}/incoming/${1}${upload_ext} ${upload_dir}/live/${1}.zip
    mv ${1}${upload_ext} ${1}.zip
    cd "${cwd}"
}

echo "=====-----=====-----=====-----=====-----=====-----=====-----=====-----" >> boost-reports-time.log
build_all 2>&1 | tee boost-reports.log
