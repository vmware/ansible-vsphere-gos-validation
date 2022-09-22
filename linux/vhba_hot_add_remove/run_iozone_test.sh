#!/bin/bash
# Copyright 2021-2022 VMware, Inc.
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
test_result=0

function exec_cmd()
{
    local cmd="$@"
    output=""
    ret=0

    echo -e "Execute command: $cmd"
    output=`eval $cmd`
    ret=$?
    echo "Return Code: $ret"
    if [ $ret != 0 ]; then
       test_result=$ret
    fi

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

    if [ ! -e "$testdir_path" ]; then
        printf "Create folder $testdir_path:  "
        mkdir $testdir_path 
        if [ $? -eq 0 ]; then 
            echo "SUCCEED"
        else
            echo "FAIL"
        fi
    fi

    
    iozone_file="$testdir_path/iozone.csv"
    md5_file="$testdir_path/md5"
    if [ ! -e "$iozone_file" ]; then
        # Get partition size
        part_size=`lsblk -o NAME,SIZE,TYPE | grep -i part | grep -i ${part_name} | awk '{print $2}'`
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
        if [ $part_size -gt 128 ]; then
            ${IOZONE_PATH} -Ra -g 128M -i 0 -i 1 -b "$iozone_file"
        else
            ${IOZONE_PATH} -Ra -g ${test_size}M -i 0 -i 1 -b "$iozone_file"
        fi

        # Generate md5sum
        if [ -e "$iozone_file" ]; then
            exec_cmd "md5sum $iozone_file >$md5_file"
        fi

        #Return to work dir
        cd "$cwd"
    else
        # Check md5sum
        if [ -e "$md5_file" ]; then
            echo "Check MD5 checksum of $iozone_file"
            md5sum -c $md5_file
        else
            exec_cmd "md5sum $iozone_file >$md5_file"
        fi
    fi
}


function test_partitions()
{
    local dev_name="$1"
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
        exec_cmd "mkdir -p $mount_point"
    fi

    mount | grep -i "$part_name" >/dev/null
    if [ $? -ne 0 ]; then
        exec_cmd "mount ${mount_ops} $part_path $mount_point >/dev/null 2>&1"
        printf "Mount $part_path to $mount_point: "
        if [ $ret -ne 0 ] ; then
            echo "FAIL"
            if [ "$PART_FS" == "ext4" ] && [ "$mount_ops" == "-o dax" ]; then
                printf "Retry without option \"${mount_ops}\": "
                mount $part_path $mount_point && echo "SUCCEED" || echo "FAIL"
            else
                echo "Error: Could not mount $part_path to $mount_point"
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

    umount $mount_point
}


for dev_name in $1; do
    echo -e "\n>>>>>>>>>>>>>Start to test /dev/$dev_name<<<<<<<<<<<<<<<<<<\n"
    test_partitions "$dev_name"
    echo -e "\n>>>>>>>>>>>>>End of testing /dev/$dev_name<<<<<<<<<<<<<<<<<<\n"
done

exit $test_result
