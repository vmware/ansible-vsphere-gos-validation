#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Send a DHCPRELEASE packet to a DHCP server to release the current IP address.
Compatible with Python 2.x and 3.x without external dependencies.
Works on various Linux distributions (Debian, Redhat, Ubuntu, SLES, etc.).
"""

import socket
import struct
import sys
import random
import fcntl
import glob

def get_default_interface():
    try:
        with open('/proc/net/route', 'r') as f:
            for line in f:
                parts = line.strip().split()
                # Destination is parts[1], '00000000' indicates the default route
                if len(parts) > 1 and parts[1] == '00000000':
                    return parts[0]
    except Exception:
        pass
    return None

def get_mac_address(iface):
    try:
        with open('/sys/class/net/%s/address' % iface, 'r') as f:
            return f.read().strip()
    except Exception:
        return None

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        if sys.version_info[0] >= 3:
            ifname_bytes = ifname.encode('utf-8')
        else:
            ifname_bytes = ifname
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', ifname_bytes[:15])
        )[20:24])
    except Exception:
        return None

def get_dhcp_server(ifname):
    # 1. Try to find from common lease files
    lease_patterns = [
        '/var/lib/dhcp/dhclient.%s.leases' % ifname,
        '/var/lib/dhcp/dhclient.leases',
        '/var/lib/dhclient/dhclient-%s.leases' % ifname,
        '/var/lib/dhclient/dhclient.leases',
        '/var/lib/NetworkManager/dhclient-*.lease',
        '/var/lib/NetworkManager/internal-*.lease'
    ]
    
    actual_files = []
    for pattern in lease_patterns:
        actual_files.extend(glob.glob(pattern))
        
    for lf in actual_files:
        try:
            with open(lf, 'r') as f:
                lines = f.readlines()
                # Read backwards to get the latest lease
                for line in reversed(lines):
                    line = line.strip()
                    if line.startswith('dhcp-server-identifier'):
                        return line.split()[1].rstrip(';')
        except Exception:
            continue
            
    # 2. Try systemd-networkd
    try:
        idx = None
        with open('/sys/class/net/%s/ifindex' % ifname, 'r') as f:
            idx = f.read().strip()
        if idx:
            with open('/run/systemd/netif/leases/%s' % idx, 'r') as f:
                for line in f:
                    if line.startswith('SERVER_ADDRESS='):
                        return line.split('=')[1].strip()
    except Exception:
        pass

    # 3. Fallback to default gateway
    try:
        with open('/proc/net/route', 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) > 2 and parts[1] == '00000000' and parts[0] == ifname:
                    gw_hex = parts[2]
                    return socket.inet_ntoa(struct.pack('<L', int(gw_hex, 16)))
    except Exception:
        pass
        
    return None

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
        print("Usage: %s [interface] [client_ip] [server_ip] [mac_address]" % sys.argv[0])
        print("Example: %s" % sys.argv[0])
        print("Example: %s eth0" % sys.argv[0])
        print("Example: %s eth0 192.168.1.100 192.168.1.1 00:11:22:33:44:55" % sys.argv[0])
        sys.exit(1)

    # Interface
    if len(sys.argv) > 1 and sys.argv[1].lower() != 'auto':
        iface = sys.argv[1]
    else:
        iface = get_default_interface()
        if not iface:
            print("Failed to auto-detect default interface. Please provide it manually.")
            sys.exit(1)
        print("Auto-detected default interface: %s" % iface)
    
    # Client IP
    if len(sys.argv) >= 3 and sys.argv[2].lower() != 'auto':
        client_ip = sys.argv[2]
    else:
        client_ip = get_ip_address(iface)
        if not client_ip:
            print("Failed to auto-detect IP address for interface %s. Please provide it manually." % iface)
            sys.exit(1)

    # Server IP
    if len(sys.argv) >= 4 and sys.argv[3].lower() != 'auto':
        server_ip = sys.argv[3]
    else:
        server_ip = get_dhcp_server(iface)
        if not server_ip:
            print("Failed to auto-detect DHCP server IP for interface %s. Please provide it manually." % iface)
            sys.exit(1)

    # MAC Address
    if len(sys.argv) >= 5 and sys.argv[4].lower() != 'auto':
        mac_str = sys.argv[4]
    else:
        mac_str = get_mac_address(iface)
        if not mac_str:
            print("Failed to auto-detect MAC address for interface %s. Please provide it manually." % iface)
            sys.exit(1)

    # Parse MAC address
    try:
        mac_parts = [int(x, 16) for x in mac_str.split(':')]
        if len(mac_parts) != 6:
            raise ValueError("Invalid MAC length")
        mac_bytes = struct.pack('!6B', *mac_parts)
    except Exception as e:
        print("Invalid MAC address format: %s" % mac_str)
        sys.exit(1)

    # Build DHCP Release packet
    op = 1 # BOOTREQUEST
    htype = 1 # Ethernet
    hlen = 6 # MAC length
    hops = 0
    xid = random.randint(0, 0xFFFFFFFF)
    secs = 0
    flags = 0

    try:
        ciaddr = socket.inet_aton(client_ip)
        yiaddr = socket.inet_aton('0.0.0.0')
        siaddr = socket.inet_aton('0.0.0.0')
        giaddr = socket.inet_aton('0.0.0.0')
    except Exception as e:
        print("Invalid IP address format: %s" % e)
        sys.exit(1)

    chaddr = mac_bytes + b'\x00' * 10

    sname = b'\x00' * 64
    file_name = b'\x00' * 128

    magic_cookie = struct.pack('!4B', 0x63, 0x82, 0x53, 0x63)

    # Option 53: DHCP Message Type (7 = DHCPRELEASE)
    opt53 = struct.pack('!3B', 53, 1, 7)
    
    # Option 54: Server Identifier
    opt54 = struct.pack('!2B', 54, 4) + socket.inet_aton(server_ip)
    
    # Option 255: End
    opt255 = struct.pack('!B', 255)

    packet = struct.pack('!BBBB', op, htype, hlen, hops)
    packet += struct.pack('!I', xid)
    packet += struct.pack('!HH', secs, flags)
    packet += ciaddr
    packet += yiaddr
    packet += siaddr
    packet += giaddr
    packet += chaddr
    packet += sname
    packet += file_name
    packet += magic_cookie
    packet += opt53
    packet += opt54
    packet += opt255

    # Padding to meet minimum BOOTP packet size (300 bytes)
    if len(packet) < 300:
        packet += b'\x00' * (300 - len(packet))

    print("Preparing to send DHCPRELEASE:")
    print("  Interface:  %s" % iface)
    print("  Client IP:  %s" % client_ip)
    print("  Server IP:  %s" % server_ip)
    print("  MAC Addr:   %s" % mac_str)

    # Send packet
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Try to bind to port 68
        try:
            sock.bind(('0.0.0.0', 68))
        except Exception:
            pass

        # Try to bind to specific interface
        try:
            SO_BINDTODEVICE = 25
            if sys.version_info[0] >= 3:
                iface_bytes = iface.encode('utf-8')
            else:
                iface_bytes = iface
            sock.setsockopt(socket.SOL_SOCKET, SO_BINDTODEVICE, iface_bytes + b'\x00')
        except Exception:
            pass

        sock.sendto(packet, (server_ip, 67))
        print("Successfully sent DHCPRELEASE packet.")
    except Exception as e:
        print("Error sending packet: %s" % e)
        sys.exit(1)
    finally:
        if sock:
            sock.close()

if __name__ == '__main__':
    main()
