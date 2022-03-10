# Basic Info:

File name: openwrt_19.07.2_x86.ova
Created on: 03/10/2020
Openwrt version: 19.07.2
Download URL: https://downloads.openwrt.org/releases/19.07.2/targets/x86/generic/openwrt-19.07.2-x86-generic-combined-ext4.img.gz

# This VM template was built with the following:

Virtual CPU: 1
RAM: 1GB
DISK 1: 4GB (Thin Provision)
NETWORK ADAPTER 1: E1000
Hardware version: 10

# Logon info:

User/Password: root/vmware

# Openwrt License:

Refer to: https://openwrt.org/license

# Configure:

## /etc/config/network
```
config interface 'loopback'
	option ifname 'lo'
	option proto 'static'
	option ipaddr '127.0.0.1'
	option netmask '255.0.0.0'

config interface 'lan'
	option ifname 'eth0'
	option proto 'dhcp'

config interface 'Lan1'
	option ifname 'eth1'
	option _orig_ifname 'eth1'
	option _orig_bridge 'false'
	option proto 'static'
	option ipaddr '192.168.192.1'
	option netmask '255.255.255.0'

config interface 'Lan2'
	option proto 'static'
	option ifname 'eth2'
	option ipaddr '192.168.193.1'
	option netmask '255.255.255.0'

config interface 'Lan3'
	option proto 'static'
	option ifname 'eth3'
	option ipaddr '192.168.194.1'
	option netmask '255.255.255.0'
```
