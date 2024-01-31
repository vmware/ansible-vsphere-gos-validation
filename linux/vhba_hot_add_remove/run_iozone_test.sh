#!/bin/sh
# Copyright 2021-2024 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#set -x

output=""
ret=0
cwd=`pwd`
os_distribution=`uname -s`
os_arch=`uname -p`
echo "OS distribution is $os_distribution"
MOUNT_OPTS=""
TEST_SIZE="128M"
if [[ "$os_distribution" =~ FreeBSD ]]; then
    IOZONE_PATH="/usr/local/bin/iozone"
    PART_FS="ufs"
    MOUNT_OPTS="-t ${PART_FS}"
    if [ "$os_arch" == "i386" ]; then
        TEST_SIZE="128K"
    fi
else
    IOZONE_PATH="/tmp/iozone"
    PART_FS="ext4"
fi

function exec_cmd()
{
    local cmd="$@"
    output=""
    ret=0

    echo -e "Execute command: $cmd"
    output=`eval $cmd`
    ret=$?
    echo "Return Code: $ret"

    if [ "X$output" != "X" ]; then
        echo -e "Command output: \n$output"
    fi

    echo -e ""
}

function run_iozone()
{
    local mount_point="$1"
    local testdir_path="${mount_point}/testdir"
    if [ -e "$testdir_path" ]; then
        rm -rf $testdir_path
    fi
    printf "Create folder $testdir_path:  "
    exec_cmd "mkdir -p $testdir_path"
    if [ $ret -eq 0 ]; then
        echo "SUCCEED"
    else
        echo "FAIL"
        exit $ret
    fi

    iozone_file="$testdir_path/iozone.csv"
    echo "Go to $testdir_path"
    cd "$testdir_path"
    echo "Run iozone on $mount_point"
    ${IOZONE_PATH} -Ra -g ${TEST_SIZE} -i 0 -i 1 -b "$iozone_file"
    ret=$?
    if [ $ret -ne 0 ]; then
        echo "Run iozone test failed"
        exit $ret
    fi

    #Return to work dir
    cd "$cwd"
}

run_iozone "$1"
exit 0
