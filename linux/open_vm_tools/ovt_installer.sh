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

for cmd in  "${commands[@]}"; do
    echo ">>>Beginning of command: $cmd<<<"
    eval "$cmd"
    rc=$?
    if [ $rc -ne 0 ]; then
        echo "Failed to execute command: $cmd"
        exit $rc;
    fi
    echo ">>>End of command: $cmd<<<"
    echo ""
done
