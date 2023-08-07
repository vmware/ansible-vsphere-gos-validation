#!/bin/bash
# Copyright 2021-2023 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#set -x

output=""
ret=0
dev_list=""
dev_num=0
cwd=`pwd`
EXCLUDE=""
BOOT_DISK=""
HAS_PMEM="false"
HAS_NVME="false"
HAS_PVSCSI="false"
IOZONE_PATH="/tmp/iozone"
PART_FS="ext4"
os_distribution=`uname -s`

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
    local part_name="$1"
    local part_path="/dev/$part_name"
    local mount_point="/mnt/$part_name"
    local testdir_path="${mount_point}/testdir"

    # partition size in mb
    local size_unit="M"

    local part_size=
    local test_size=

    if [ -e "$testdir_path" ]; then
        rm -rf $testdir_path
    fi
    printf "Create folder $testdir_path:  "
    exec_cmd "mkdir -m 777 $testdir_path"
    if [ $ret -eq 0 ]; then
        echo "SUCCEED"
    else
        echo "FAIL"
        exit $ret
    fi

    iozone_file="$testdir_path/iozone.csv"
    # Get disk size
    if [[ "$os_distribution" =~ FreeBSD ]]; then
        part_size=`geom disk list ${dev_name} | head -n 10 | grep Mediasize | awk '{print $3}' | cut -d '(' -f2 | cut -d ')' -f1`
    else
        part_size=`lsblk -o NAME,SIZE,TYPE | grep -i part | grep -i ${part_name} | awk '{print $2}'`
    fi
    echo "Partition $part_path size is $part_size"

    if [[ "$part_size" =~ .G ]]; then
        part_size=`echo $part_size | tr -d 'G'`
        size_unit="G"
        test_size=128
    else
        part_size=`echo $part_size | tr -d 'M'`
        size_unit="M"
        if [ $part_size -gt 128 ]; then
            test_size=128
        else
            test_size=$(($part_size/2))
        fi
    fi

    if [ "X$test_size" == "X" ] || [ "X$test_size" == "X0" ]; then
        echo "Error: Incorrect size value for iozone"
        exit 1
    fi

    echo "Go to $testdir_path"
    cd "$testdir_path"
    echo "Run iozone on $part_path" || continue
    # Run iozone testing
    if [ $(echo "$part_size > 128"|bc) -eq 1 ]; then
        ${IOZONE_PATH} -Ra -g 128M -i 0 -i 1 -b "$iozone_file"
    else
        ${IOZONE_PATH} -Ra -g ${test_size}M -i 0 -i 1 -b "$iozone_file"
    fi

    ret=$?

    if [ $ret -ne 0 ]; then
        echo "iozone test failed"
        exit $ret
    fi

    #Return to work dir
    cd "$cwd"
}


function test_partitions()
{
    dev_name="$1"
    local dev_path="/dev/$1"
    local part_idx=1

    # Number  Start   End     Size    File system  Name     Flags
    #  1      1049kB  2147MB  2146MB  ext4         primary

    if [[ "${dev_name}" =~ pmem. ]] && [[ "$PART_FS" != "btrfs" ]]; then
        mount_ops="-o dax"
    else
        mount_ops=""
    fi

    if [[ "$dev_name" =~ sd. ]]; then
        part_name="${dev_name}${part_idx}"
    else
        part_name="${dev_name}p${part_idx}"
    fi

    part_path="/dev/${part_name}"
    mount_point="/mnt/${part_name}"
    if [ ! -e "$mount_point" ]; then
        echo "Create mount point $mount_point"
        exec_cmd "mkdir -p -m 777 $mount_point"
    fi

    mount | grep -i "$part_name" >/dev/null
    if [ $? -ne 0 ]; then
        exec_cmd "mount ${mount_ops} $part_path $mount_point >/dev/null 2>&1"
        printf "Mount $part_path to $mount_point: "
        if [ $ret -ne 0 ] ; then
            echo "FAIL"
            if [ "$PART_FS" == "ext4" ] && [ "$mount_ops" == "-o dax" ]; then
                echo "Retry mount without option \"${mount_ops}\": "
                exec_cmd "mount $part_path $mount_point && echo 'SUCCEED' || echo 'FAIL'"
            fi

            if [ $ret -ne 0 ] ; then
                echo "FAIL"
                echo "Could not mount $part_path to $mount_point"
                exit $ret
            fi
        else
            echo "SUCCEED"
        fi
    fi

    # Run iozone or check iozone file's md5sum
    if [  -e ${IOZONE_PATH} ]; then
        run_iozone "$part_name"
    fi

    # Print disk's partition again
    echo "${dev_path} partitions:"
    exec_cmd "fdisk -l ${dev_path}"

    exec_cmd "umount $mount_point"
}

function freebsd_test_partitions()
{
    dev_name="$1"
    local dev_path="/dev/$1"

    part_name="${dev_name}p1"
    part_path="/dev/${part_name}"

    # FreeBSD won't setup partition table but take the whole disk"
    iozone_prepared=0
    mount_point="/mnt/${part_name}"
    try_count=1
   
    until [ $try_count -gt 10 ]
    do
        echo "Prepare for iozone test (try $try_count time) ..."
        try_count=$((try_count+1))

        mount | grep -i "$part_name" >/dev/null
        if [ $? -eq 0 ]; then
            echo "umount ${part_path} : "
            exec_cmd "umount $mount_point >/dev/null 2>&1"
            if [ $ret -ne 0 ] ; then
                echo "FAIL"
                echo "Could not umount $part_path"
                exit $ret
            fi
        fi

        echo "Format the disk $part_path : "
        exec_cmd "newfs -EU $part_path >/dev/null 2>&1"
        if [ $ret -ne 0 ] ; then
            echo "FAIL"
            continue
        fi

        echo "Check the dir $part_path"
        mount_point="/mnt/${part_name}"
        if [ ! -e "$mount_point" ]; then
            echo "Create mount point $mount_point : "
            exec_cmd "mkdir -p -m 777 $mount_point >/dev/null 2>&1"
            if [ $ret -ne 0 ] ; then
                echo "FAIL"
                continue
            fi
        fi

        mount | grep -i "$part_name" >/dev/null
        if [ $? -ne 0 ]; then
            printf "Mount $part_path to $mount_point : "
            exec_cmd "mount $part_path $mount_point >/dev/null 2>&1"
            if [ $ret -ne 0 ] ; then
                echo "FAIL"
                continue
            fi
        fi

        printf "Create folder ${mount_point}/testdir : "
        exec_cmd "mkdir -m 777 ${mount_point}/testdir >/dev/null 2>&1"
        if [ $ret -nq 0 ] ; then
            echo "FAIL"
            continue
        else
            iozone_prepared=1
            break
        fi
    done

    if [ $iozone_prepared -eq 0 ] ; then
        echo "Failed to Prepare for iozone test after try $try_count times"
        exit $ret
    fi

    IOZONE_PATH="/usr/local/bin/iozone"
    # Run iozone or check iozone file's md5sum
    if [  -e ${IOZONE_PATH} ]; then
        run_iozone "$part_name"
    fi

    # Print disk's partition again
    echo "${dev_path} partitions:"
    exec_cmd "geom disk list ${dev_path}"
    exec_cmd "umount $mount_point"
}

for dev_name in $1; do
    echo -e "\n>>>>>>>>>>>>>Start to test /dev/$dev_name<<<<<<<<<<<<<<<<<<\n"
    if [[ "$os_distribution" =~ FreeBSD ]]; then
        freebsd_test_partitions "$dev_name"
    else
        test_partitions "$dev_name"
    fi
    echo -e "\n>>>>>>>>>>>>>End of testing /dev/$dev_name<<<<<<<<<<<<<<<<<<\n"
done

exit 0
