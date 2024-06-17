#!/bin/sh
# Set hostname
sysrc hostname="FreeBSD-{{ current_test_timestamp }}"

# Set Time Zone to UTC
echo "Setting Time Zone to UTC ..."
/bin/cp /usr/share/zoneinfo/UTC /etc/localtime
/usr/bin/touch /etc/wall_cmos_clock
/sbin/adjkerntz -a

echo "Set network interface with DHCP IP assignment ..." > /dev/ttyu0
ifdev=$(ifconfig | grep '^[a-z]' | cut -d: -f1 | head -n 1)
echo "Get ifname ${ifdev}" > /dev/ttyu0
sysrc ifconfig_${ifdev}=DHCP

# Get DHCP for nic0
echo "Get IP with dhclient ..." > /dev/ttyu0
dhclient ${ifdev}
sleep 15
echo "Check network ..." > /dev/ttyu0
ifconfig > /dev/ttyu0

# Set Proxy.
{% if http_proxy_vm is defined and http_proxy_vm %}
setenv HTTP_PROXY {{ http_proxy_vm }}
{% endif %}

# Installing packages
chmod 0755 /etc/freebsd_install_pkgs.sh
/bin/sh /etc/freebsd_install_pkgs.sh

# Add new user. 
{% if new_user is defined and new_user != 'root' %}
echo "{{ vm_password }}" | pw useradd {{ new_user }} -s /bin/sh -d /home/{{ new_user }} -m -g wheel -h 0
echo '{{ new_user }} ALL=(ALL:ALL) ALL' >> /usr/local/etc/sudoers
{% endif %}

# Set password of root user
echo "{{ vm_password }}" | pw -V /etc usermod root -h 0

# Enable root login via ssh
echo "Enable root login via ssh ..." > /dev/ttyu0
mkdir -p -m 700 /root/.ssh
echo "{{ ssh_public_key }}" > /root/.ssh/authorized_keys
chown -R root /root/.ssh
chmod 0644 /root/.ssh/authorized_keys
# We can't ssh to VM with empty password for root user
sed -i .bak -e 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i '' -e 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config

# Enable service
echo "Enable service ..." > /dev/ttyu0
sysrc sshd_enable="YES"
sysrc ntpd_enable="YES"
sysrc ntpd_sync_on_start="YES"

# Eanble ZFS
sysrc zfs_enable="YES"

# Configure KDE desktop
echo "proc      /proc       procfs  rw  0   0" >> /etc/fstab
sysrc dbus_enable="YES"
sysrc sddm_enable="YES"

# Autologin to desktop environment
echo "[Autologin]" >> /usr/local/etc/sddm.conf
echo "User={{ new_user }}" >> /usr/local/etc/sddm.conf
echo "Session=plasma.desktop" >> /usr/local/etc/sddm.conf

# Enable GEOM label
echo "Enable disk label ..." > /dev/ttyu0
sed -i '' 's/kern.geom.label.disk_ident.enable="0"/kern.geom.label.disk_ident.enable="1"/' /boot/loader.conf
sed -i '' 's/kern.geom.label.gptid.enable="0"/kern.geom.label.gptid.enable="1"/' /boot/loader.conf
echo 'kern.geom.label.gpt.enable="1"' >>/boot/loader.conf
echo 'kern.geom.label.ufs.enable="1"' >>/boot/loader.conf
echo 'kern.geom.label.ufsid.enable="1"' >>/boot/loader.conf

# Reducing boot menu delay
echo "Reducing boot menu delay ..." > /dev/ttyu0
echo 'autoboot_delay="3"' >> /boot/loader.conf
