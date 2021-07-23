# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#!/bin/bash
# This script will download ActivePython3 and install it in Flatcar

if [ $# -eq 1 ]; then
    ap_python3_download_url="$1"
else
    ap_python3_download_url="https://downloads.activestate.com/ActivePython/releases/3.6.0.3600/ActivePython-3.6.0.3600-linux-x86_64-glibc-2.3.6-401834.tar.gz"
fi

# ActivePython3 binary path
ap_python3_bin_dir="/opt/bin"
ap_python3_bin_path="/opt/bin/python3"

# If python3 has been installed, exit.
if [ -f "$ap_python3_bin_path" ]; then
    echo "$ap_python3_bin_path already exists."
    exit 0
fi

#Create a temporary directory for downloading ActivePython3
ap_python3_download_dir=$(/usr/bin/mktemp -d -t ap-XXXXXX)
echo "Temporary directory $ap_python3_download_dir is created for downloading ActivePython3"

ap_python3_package_file_name=$(echo $ap_python3_download_url | xargs basename)
ap_python3_download_dest="$ap_python3_download_dir/$ap_python3_package_file_name"
ap_python3_extract_path="$ap_python3_download_dir"
ap_python3_install_path="/opt/active_python"

echo "Downloading $ap_python3_download_url ..."
wget -q --no-check-certificate $ap_python3_download_url -O $ap_python3_download_dest
if [ $? -ne 0 ]; then
    echo "Failed to download $ap_python3_download_url"
    exit 1
fi

echo "Extracting $ap_python3_download_dest to $ap_python3_extract_path ..."
tar -xf $ap_python3_download_dest -C $ap_python3_extract_path
if [ $? -ne 0 ]; then
    echo "Failed to extract $ap_python3_download_dest"
    exit 1
fi

if [ ! -e $ap_python3_bin_dir ]; then
    echo "Create ActivePython3 binary directory: $ap_python3_bin_dir"
    mkdir -p $ap_python3_bin_dir
fi

if [ ! -e $ap_python3_install_path ]; then
   echo "Create ActivePython3 install directory: $ap_python3_install_path"
   mkdir -p "$ap_python3_install_path"
fi

echo "Installing ActivePython3 ..."
ap_python3_install_script=$(find $ap_python3_extract_path -name 'install.sh')
chmod +x $ap_python3_install_script
$ap_python3_install_script -I $ap_python3_install_path
rc=$?
if [ $rc -ne 0 ]; then
    echo "Failed to install ActivePython3"
    exit $rc
else
    echo "Create symbolic link for easy_install"
    ln -sf "$ap_python3_install_path/bin/easy_install" "$ap_python3_bin_dir/easy_install"

    echo "Create symbolic links for pip"
    ln -sf "$ap_python3_install_path/bin/pip3" "$ap_python3_bin_dir/pip"
    ln -sf "$ap_python3_install_path/bin/pip3" "$ap_python3_bin_dir/pip3"

    echo "Create symbolic links for python3"
    ln -sf "$ap_python3_install_path/bin/python3" "$ap_python3_bin_dir/python"
    ln -sf "$ap_python3_install_path/bin/python3" "$ap_python3_bin_dir/python3"

    echo "Create symbolic link for virtualenv"
    ln -sf "$ap_python3_install_path/bin/virtualenv" "$ap_python3_bin_dir/virtualenv"

    echo "Remove directory $ap_python3_download_dir"
    rm -rf $ap_python3_download_dir

    # Add /opt/bin to PATH for python auto discovery
    echo 'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/opt/bin' >>/etc/environment

    python_version=$($ap_python3_bin_dir/python -V)
    rc=$?
    if [ $rc -eq 0 ]; then
        echo "$python_version is successfully installed"
    else
        echo "Failed to create symbolic link for python3"
    fi
    exit $rc
fi
