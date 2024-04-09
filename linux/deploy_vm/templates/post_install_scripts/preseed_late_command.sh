#!/bin/bash
# Get OS information
{% include 'get_os_info.sh' %}

# Install required packages
required_pkgs="open-vm-tools"
{% if unattend_installer == 'Ubuntu-Ubiquity' %}
# Ubuntu Desktop required packages
required_pkgs="$required_pkgs open-vm-tools-desktop build-essential openssh-server vim locales cloud-init rdma-core rdmacm-utils ibverbs-utils"
{% elif unattend_installer == 'Debian' %}
# Debian required packages
required_pkgs="$required_pkgs open-vm-tools-desktop cloud-init debconf-utils rdma-core rdmacm-utils ibverbs-utils"
{% elif unattend_installer == 'Pardus' %}
# Pardus required packages
required_pkgs="$required_pkgs openssh-server build-essential open-vm-tools sg3-utils vim python3-apt dbus lsof"
if [ "X$OS_DM" != "X" ]; then
  required_pkgs="$required_pkgs open-vm-tools-desktop"
fi
{% endif %}

{% include 'apt_install_pkgs.sh' %}

# Set default locale
{% include 'set_locale.sh' %}

{% include 'config_ssh.sh' %}

{% include 'enable_auto_login.sh' %}

{% include 'disable_greeter.sh' %}

{% include 'disable_screen_saver.sh' %}
