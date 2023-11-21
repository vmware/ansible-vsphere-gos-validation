#!/bin/sh
echo "{{ autoinstall_start_msg }}"
echo "Installer environment variables: "
env | sort

ip_addr=$(ip -o -f inet addr show | grep -v 127.0.0.1 | awk '{print $4}')
echo "DHCP IPv4 address at pre-install: $ip_addr"

echo "Boot command"
cat /proc/cmdline
