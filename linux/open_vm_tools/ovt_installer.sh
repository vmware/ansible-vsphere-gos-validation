#!/usr/bin/env bash
##########################################################
# Copyright 2024 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#
##########################################################
#
# Usage: ovt_installer.sh [configure_options]
# For example,
#    ovt_installer.sh
#    ovt_installer.sh --disable-deploypkg --without-icu
#
if [ $# -ge 1 ]; then
    config_opts=$@
else
    config_opts=""
fi

# Cloud-init GOSC requires open-vm-tools binaries under /usr/bin
# and plugins under /usr/lib. To support cloud-init GOSC, it is
# recommended to set "--prefix=/usr".
if [ "X$INSTALL_PREFIX" == "X" ]; then
    INSTALL_PREFIX="/usr"
fi

commands=("autoreconf -f -i"
          "./configure --prefix=$INSTALL_PREFIX $config_opts"
          "make"
          "make install"
          "ldconfig")
rc=0

CURRENT_DIR=$PWD

system=$(uname -s)
if [ "$system" == "FreeBSD" ]; then
    # Create the directory path of tools.conf on FreeBSD
    mkdir -p $INSTALL_PREFIX/share/vmware-tools/
    chmod a+rx $INSTALL_PREFIX/share/vmware-tools/

    # Workaround for compiliing error on FreeBSD 14
    freebsd_version=$(freebsd-version | cut -d '.' -f 1)
    echo "FreeBSD release version is $freebsd_version"
    freebsd_patches_dir="/usr/ports/emulators/open-vm-tools/files"

    module_patches=`find /usr/ports/emulators/open-vm-kmod/files -name 'patch-*' | grep -v Makefile`
    cd modules/freebsd/
    for module_patch in $module_patches; do
        echo "Applying patch $module_patch"
        patch <$module_patch
        if [ $? -ne 0 ]; then
            echo "ERROR: Failed to apply patch $module_patch" >&2
        fi
    done
    cd $CURRENT_DIR

    ovt_patches=`find /usr/ports/emulators/open-vm-tools/files -name 'patch-*' | grep -E 'vmmemctl_os.c|vmblock_vfsops.c|dndcp_stringxx_string.hh'`
    for ovt_patch in $ovt_patches; do
        echo "Applying patch $ovt_patch"
        patch <$ovt_patch
        if [ $? -ne 0 ]; then
            echo "ERROR: Failed to apply patch $ovt_patch" >&2
        fi
    done
fi

cmd_index=1
for cmd in  "${commands[@]}"; do
    echo ">>>Beginning of command: $cmd<<<"
    eval "$cmd 2>stderr.log" 
    rc=$?
    if [ $rc -ne 0 ]; then
        echo "ERROR: Failed to execute command '$cmd'" >&2
        cat 'stderr.log' >&2
        exit $cmd_index;
    fi
    echo ">>>End of command: $cmd<<<"
    echo ""
    cmd_index=$((cmd_index+1))
done
