#!/bin/bash

LOG_ROOT=tmp
SCRIPT_NAME=download-logs.sh
SCRIPT_URL=$1
LOG_DIR=

function make_tmpdir() {
    local tmp_urlfile=$(mktemp --tmpdir zuullog-url-XXXX)
    echo $1 > $tmp_urlfile

    # Extract patch ID, PS and name of test job from url to be use to dir name.
    # An example of the url is here.
    # https://f441cebd08a9e5a7d2e3-414923073fac46561b63670d4adbb9d2.ssl.cf1.rackcdn.com/872690/5/check/openstack-tox-py38/860ae88/download-logs.sh
    if [[ $1 =~ ^https://(.*)ssl.cf[0-9+].rackcdn.com(.*)$ ]]; then
        local tmpdir=$(cut -f 4,5,7 -d / ${tmp_urlfile})
    # https://storage.bhs.cloud.ovh.net/v1/AUTH_dcaab5e32b234d56b626f72581e3644c/zuul_opendev_logs_c5f/873217/4/check/openstack-tox-py310/c5f38b6/download-logs.sh
    elif [[ $1 =~ ^https://storage.(.*).cloud.ovh.net(.*)$ ]]; then
        local tmpdir=$(cut -f 7,8,10 -d / ${tmp_urlfile})
    else
        echo "FAILURE: No supported url "$1
        return 1
    fi

    if [ -z ${tmpdir} ]; then
        echo "FAILURE: Invalid URL "${1}
    else
        LOG_DIR=${LOG_ROOT}/${tmpdir}
        mkdir -p ${LOG_DIR}
        echo "Created log dir: ${LOG_DIR}"
    fi
    return 0
}

function download_script() {
    wget -O ${LOG_DIR}/${SCRIPT_NAME} ${SCRIPT_URL}
    DOWNLOAD_DIR=${LOG_DIR} . ${LOG_DIR}/${SCRIPT_NAME}
}

function show_help() {
    echo "usage: $(basename $0) [-h] SCRIPT_URL"
}

while getopts h- opt; do
    case ${opt} in
        h) show_help
           exit
           ;;
    esac
done

if [ -z ${SCRIPT_URL} ]; then
    show_help
    exit
else
    make_tmpdir ${SCRIPT_URL}
    download_script
fi

