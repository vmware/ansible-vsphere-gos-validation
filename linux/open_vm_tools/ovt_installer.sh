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
#    ovt_installer.sh --without-deploy --without-icu
#
if [ $# -ge 1 ]; then
    config_opts=$@
else
    config_opts=""
fi

# Cloud-init GOSC requires open-vm-tools binaries under /usr/bin
# and plugins under /usr/lib. So here sets install prefix to /usr
commands=("autoreconf -f -i"
          "./configure --prefix=/usr $config_opts"
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
