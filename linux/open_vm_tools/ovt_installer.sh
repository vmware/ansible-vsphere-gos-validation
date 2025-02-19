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

system=$(uname -s)
if [ "$system" == "FreeBSD" ]; then
    # Create the directory path of tools.conf on FreeBSD
    mkdir -p $INSTALL_PREFIX/share/vmware-tools/
    chmod a+rx $INSTALL_PREFIX/share/vmware-tools/

    # Workaround for compiliing error on FreeBSD 14
    freebsd_version=$(freebsd-version | cut -d '.' -f 1)
    echo "FreeBSD release version is $freebsd_version"
    freebsd_patches_dir="/usr/ports/emulators/open-vm-tools/files"
    ovt_patches=""
    if [ $freebsd_version -ge 14 ]; then
        ovt_patches="$freebsd_patches_dir/patch-modules_freebsd_vmmemctl_os.c \
                     $freebsd_patches_dir/patch-modules_freebsd_vmblock_vfsops.c"
    elif [ $freebsd_version -ge 13 ]; then
        ovt_patches="$freebsd_patches_dir/patch-services_plugins_dndcp_stringxx_string.hh"
    fi

    if [ "$ovt_patches" != "" ]; then
        for ovt_patch in $ovt_patches; do
            if [ -e "$ovt_patch" ]; then
                 echo "Applying patch $ovt_patch"
                 patch <$ovt_patch
            fi
        done
    fi
fi

for cmd in  "${commands[@]}"; do
    echo ">>>Beginning of command: $cmd<<<"
    eval "$cmd"
    rc=$?
    if [ $rc -ne 0 ]; then
        echo "Failed to execute command: $cmd" >&2
        exit $rc;
    fi
    echo ">>>End of command: $cmd<<<"
    echo ""
done
