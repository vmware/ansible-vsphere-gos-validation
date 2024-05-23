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

# Create the directory path of tools.conf on FreeBSD
system=$(uname -s)
if [ "$system" == "FreeBSD" ]; then
    mkdir -p $INSTALL_PREFIX/share/vmware-tools/
    chmod a+rx $INSTALL_PREFIX/share/vmware-tools/

    # Workaround for compiliing error on FreeBSD 14
    freebsd_version=$(freebsd-version | cut -d '.' -f 1)
    echo "FreeBSD release version is $freebsd_version"
    if [ $freebsd_version -ge 14 ]; then
        vmmemctl_patch="/usr/ports/emulators/open-vm-tools/files/patch-modules_freebsd_vmmemctl_os.c"
        vmblock_patch="/usr/ports/emulators/open-vm-tools/files/patch-modules_freebsd_vmblock_vfsops.c"

        if [ -e "$vmmemctl_patch" ]; then
            echo "Applying patch $vmmemctl_patch"
            patch < $vmmemctl_patch
        fi

        if [ -e "$vmblock_patch" ]; then
            echo "Applying patch $vmblock_patch"
            patch < $vmblock_patch
        fi
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
