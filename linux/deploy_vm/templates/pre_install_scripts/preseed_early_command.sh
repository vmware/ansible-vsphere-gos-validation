#!/bin/sh
echo "{{ autoinstall_start_msg }}"
echo "Installer environment variables: "
env | sort

echo "Display network interfaces at pre-install"
ip link show
ip_addr=$(ip -o -f inet addr show | grep -v 127.0.0.1 | awk '{print $4}')
if [ "X$ip_addr" != "X" ]; then
    echo "{{ autoinstall_ipv4_msg }}$ip_addr"
else
    echo "No IP address obtained at pre-install"
fi

echo "Boot command"
cat /proc/cmdline
