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

{% if unattend_installer == 'Pardus' %}
# Force Pardus installer to use CDROM packages for GRUB by cleaning online repos from /target
mkdir -p /usr/lib/live-installer.d /usr/lib/post-base-installer.d /usr/lib/pre-pkgsel.d
cat << 'EOF' > /tmp/05clean-target-apt
#!/bin/sh
logger -t clean-target-apt "Cleaning /target online repos to enforce CDROM installation"
echo "clean-target-apt: Removing online repos from /target" >/dev/ttyS0 2>/dev/null || true
rm -rf /target/etc/apt/sources.list.d/*
rm -f /target/var/lib/apt/lists/*depo* /target/var/lib/apt/lists/*http* /target/var/lib/apt/lists/*ftp* 2>/dev/null || true
exit 0
EOF
chmod +x /tmp/05clean-target-apt
cp -f /tmp/05clean-target-apt /usr/lib/live-installer.d/05clean-target-apt
cp -f /tmp/05clean-target-apt /usr/lib/post-base-installer.d/05clean-target-apt
cp -f /tmp/05clean-target-apt /usr/lib/pre-pkgsel.d/05clean-target-apt
{% endif %}
