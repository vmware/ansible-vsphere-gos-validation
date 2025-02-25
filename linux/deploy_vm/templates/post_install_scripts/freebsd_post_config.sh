#!/bin/sh
echo "{{ autoinstall_start_msg }}" >/dev/ttyu0

machtype=$(uname -m)
echo "Machine type is $machtype" > /dev/ttyu0

printf "Adding boot loader settings ... " >/dev/ttyu0
# Reducing boot menu delay
echo 'autoboot_delay="3"' >> /boot/loader.conf
# Enable GEOM label
sed -i '' 's/kern.geom.label.disk_ident.enable="0"/kern.geom.label.disk_ident.enable="1"/' /boot/loader.conf
sed -i '' 's/kern.geom.label.gptid.enable="0"/kern.geom.label.gptid.enable="1"/' /boot/loader.conf
echo 'kern.geom.label.gpt.enable="1"' >>/boot/loader.conf
echo 'kern.geom.label.ufs.enable="1"' >>/boot/loader.conf
echo 'kern.geom.label.ufsid.enable="1"' >>/boot/loader.conf

if [ "$machtype" != "amd64" ] && [ "$machtype" != "x86_64" ]; then
    # Workaround for FreeBSD issue https://bugs.freebsd.org/bugzilla/show_bug.cgi?id=283276
    echo 'kern.kstack_pages=8' >>/boot/loader.conf
fi
echo "DONE" >/dev/ttyu0

echo "The updated /boot/loader.conf is:" >/dev/ttyu0
cat /boot/loader.conf > /dev/ttyu0

printf "Setting hostname ... " >/dev/ttyu0
sysrc hostname="FreeBSD-{{ current_test_timestamp }}"
echo "DONE" >/dev/ttyu0

# Set Time Zone to UTC
printf "Setting Time Zone to UTC ..." >/dev/ttyu0
/bin/cp /usr/share/zoneinfo/UTC /etc/localtime
/usr/bin/touch /etc/wall_cmos_clock
/sbin/adjkerntz -a
echo "DONE" >/dev/ttyu0

printf "Getting network interface name ... " > /dev/ttyu0
ifdev=$(ifconfig | grep '^[a-z]' | cut -d: -f1 | head -n 1) >/dev/ttyu0
echo "DONE" >/dev/ttyu0

printf "Setting network interface ${ifdev} with DHCP IP assignment ... " > /dev/ttyu0
sysrc ifconfig_${ifdev}=DHCP
echo "DONE" >/dev/ttyu0

# Get DHCP IP address
printf "Getting IP address with dhclient ..." > /dev/ttyu0
dhclient -n ${ifdev} >/dev/ttyu0
sleep 10
echo "DONE" >/dev/ttyu0

ipv4=$(ifconfig ${ifdev} | awk '/inet [0-9]+/ {print $2}')
echo "{{ autoinstall_ipv4_msg }}$ipv4" > /dev/ttyu0

# Set Proxy.
{% if http_proxy_vm is defined and http_proxy_vm %}
printf "Setting proxy to {{ http_proxy_vm }} ... " >/dev/ttyu0
setenv HTTP_PROXY {{ http_proxy_vm }}
echo "DONE" >/dev/ttyu0
{% endif %}

# Installing packages
echo "Installing packages ..." > /dev/ttyu0
env ASSUME_ALWAYS_YES=YES pkg bootstrap -y

# Hit issue: reset by peer during install packages
# The open-vm-tools is not installed by default
mkdir -p /usr/local/etc/pkg/repos
mount > /dev/ttyu0
cp -rf /dist/packages/repos/FreeBSD_install_cdrom.conf /usr/local/etc/pkg/repos/FreeBSD_install_cdrom.conf
env ASSUME_ALWAYS_YES=YES pkg update -f > /dev/ttyu0

# We install packages from ISO image
# Different packages between the 32bit image and 64bit image
packages_to_install="bash sudo wget curl e2fsprogs iozone lsblk"
if [ "$machtype" == "amd64" ] || [ "$machtype" == "x86_64" ]; then
    packages_to_install="$packages_to_install xorg kde5 xf86-video-vmware sddm open-vm-tools xf86-input-vmmouse"
else
    packages_to_install="$packages_to_install open-vm-tools-nox11"
fi

failed_packages=""
for package_to_install in $packages_to_install
do
    echo "Install package $package_to_install ..." > /dev/ttyu0
    env ASSUME_ALWAYS_YES=YES pkg install -y $package_to_install
    ret=$?
    if [ $ret == 0 ]
    then 
        echo "Successfully installed the package $package_to_install from ISO repo" > /dev/ttyu0
    else
        failed_packages="$failed_packages $package_to_install"
    fi
done

# Disable ISO repo and enable default repo
rm -rf /usr/local/etc/pkg/repos/FreeBSD_install_cdrom.conf
env ASSUME_ALWAYS_YES=YES pkg update -f > /dev/ttyu0

if [ "$failed_packages" != "" ]; then
    echo "To install the following packages from offical repo: $failed_packages" > /dev/ttyu0
    for package_to_install in $failed_packages
    do
        ret=1
        try_count=1
        until [ $ret -eq 0 ] || [ $try_count -ge 10 ]
        do
            echo "Install package $package_to_install (try $try_count time) ..." > /dev/ttyu0
            env ASSUME_ALWAYS_YES=YES pkg install -y $package_to_install
            ret=$?
            try_count=$((try_count+1))
            if [ $ret -eq 0 ]; then
                echo "Successfully installed the package $package_to_install from online repo" > /dev/ttyu0
            fi
        done

        if [ $ret -ne 0 ] && [ $try_count -ge 10 ]; then
            echo "Error: Failed to install $package_to_install from ISO and online repo" > /dev/ttyu0
        fi
    done
fi

# Add new user. 
{% if new_user is defined and new_user != 'root' %}
printf "Adding new user {{ new_user }} ..." >/dev/ttyu0
echo "{{ vm_password }}" | pw useradd {{ new_user }} -s /bin/sh -d /home/{{ new_user }} -m -g wheel -h 0
echo '{{ new_user }} ALL=(ALL:ALL) ALL' >> /usr/local/etc/sudoers
echo "DONE" >/dev/ttyu0
{% endif %}

printf "Setting password of root user ..." >/dev/ttyu0
echo "{{ vm_password }}" | pw -V /etc usermod root -h 0
echo "DONE" >/dev/ttyu0

# Enable root login via ssh
printf "Enabling root login via ssh ... " > /dev/ttyu0
mkdir -p -m 700 /root/.ssh
echo "{{ ssh_public_key }}" > /root/.ssh/authorized_keys
chown -R root /root/.ssh
chmod 0644 /root/.ssh/authorized_keys
# We can't ssh to VM with empty password for root user
sed -i .bak -e 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i '' -e 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
echo "DONE" >/dev/ttyu0

# Enable services
printf "Enabling sshd and ntpd services ..." > /dev/ttyu0
sysrc sshd_enable="YES"
sysrc ntpd_enable="YES"
sysrc ntpd_sync_on_start="YES"
echo "DONE" >/dev/ttyu0

# Eanble ZFS
printf "Enable ZFS ..." > /dev/ttyu0
sysrc zfs_enable="YES"
echo "DONE" >/dev/ttyu0

# Configure KDE desktop
if [ "$machtype" == "amd64" ] || [ "$machtype" == "x86_64" ]; then
    printf "Configuring KDE desktop ... " >/dev/ttyu0
    echo "proc      /proc       procfs  rw  0   0" >> /etc/fstab
    sysrc dbus_enable="YES"
    sysrc sddm_enable="YES"
    echo "DONE" >/dev/ttyu0

    # Autologin to desktop environment
    printf "Enabling auto login for user {{ new_user }}... " >/dev/ttyu0
    echo "[Autologin]" >> /usr/local/etc/sddm.conf
    echo "User={{ new_user }}" >> /usr/local/etc/sddm.conf
    echo "Session=plasma.desktop" >> /usr/local/etc/sddm.conf
    echo "DONE" >/dev/ttyu0
fi

if [ "$BSDINSTALL_LOG" != "" ] && [ -f $BSDINSTALL_LOG ]; then
    echo "Dump BSD installer log" >/dev/ttyu0
    cat $BSDINSTALL_LOG >/dev/ttyu0
fi
echo "End of installerconfig" > /dev/ttyu0
echo "{{ autoinstall_complete_msg }}" > /dev/ttyu0

# Power off system when autoinstall completes
poweroff
