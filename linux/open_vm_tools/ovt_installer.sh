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

apply_patches() {
    local patches="$1"
    local patch_file
    for patch_file in $patches; do
        if patch -C -s -f < "$patch_file" > /dev/null 2>&1; then
            echo "Applying patch $patch_file"
            if ! patch < "$patch_file"; then
                echo "ERROR: Failed to apply patch $patch_file" >&2
            fi
        else
            echo "Skipping patch $patch_file (not applicable)"
        fi
    done
}

system=$(uname -s)
if [ "$system" == "FreeBSD" ]; then
    # Create the directory path of tools.conf on FreeBSD
    mkdir -p $INSTALL_PREFIX/share/vmware-tools/
    chmod a+rx $INSTALL_PREFIX/share/vmware-tools/

    # Workaround for compiliing error on FreeBSD 14
    freebsd_version=$(freebsd-version | cut -d '.' -f 1)
    echo "FreeBSD release version is $freebsd_version"
    freebsd_patches_dir="/usr/ports/emulators/open-vm-tools/files"

    module_patches=`find /usr/ports/emulators/open-vm-kmod/files -name 'patch-*' 2>/dev/null | grep -v Makefile`
    echo "FreeBSD module patches: ${module_patches:-<none>}"
    cd modules/freebsd/
    apply_patches "$module_patches"
    cd "$CURRENT_DIR"

    ovt_patches=`find /usr/ports/emulators/open-vm-tools/files -name 'patch-*' 2>/dev/null | grep -E 'vmmemctl_os.c|vmblock_vfsops.c|dndcp_stringxx_string.hh'`
    echo "FreeBSD OVT patches: ${ovt_patches:-<none>}"
    apply_patches "$ovt_patches"
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
