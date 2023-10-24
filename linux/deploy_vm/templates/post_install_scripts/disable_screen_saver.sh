if [[ "X$OS_DM" =~ Xgdm ]]; then
    echo "Disable GNOME blank screen, screen saver and automatic suspend"
    cat >/etc/dconf/profile/user <<EOF
user-db:user
system-db:local
EOF

    mkdir -p /etc/dconf/db/local.d
    chmod a+rx /etc/dconf/db/local.d
    cat >/etc/dconf/db/local.d/00-gdm <<EOF
[org/gnome/desktop/screensaver]
lock-enabled=false

[org/gnome/desktop/session]
idle-delay=uint32 0

[org/gnome/settings-daemon/plugins/power]
sleep-inactive-ac-timeout=0
sleep-inactive-ac-type='nothing'
EOF
    chmod a+rx /etc/dconf/db/local.d/00-gdm
    echo "Update the system dconf databases"
    dconf update
elif [[ "X$OS_DM" =~ Xlightdm ]] && [ -f /etc/xdg/autostart/light-locker.desktop ]; then
    echo "TBD: Disable XFCE screen saver and blank screen"
    echo "Hidden=true" >> /etc/xdg/autostart/light-locker.desktop
fi
