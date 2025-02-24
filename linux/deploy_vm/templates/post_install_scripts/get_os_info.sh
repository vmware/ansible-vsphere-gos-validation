echo "OS release information:"
. /etc/os-release
OS_NAME=$NAME
OS_ID=$ID
echo "OS name is $OS_NAME, release version is $VERSION_ID, codename is $VERSION_CODENAME"

echo "System environment variables:"
env | sort

# Get IPv4 address
echo "Display network interfaces"
ip -o -f inet addr show

ip_show_retries=0
while [ $ip_show_retries -lt 10 ]; do
    ip_link_name=$(ip -o -f inet addr show | grep -v '127.0.0.1' | awk '{print $2}')
    if [ "X$ip_link_name" != "X" ]; then
        echo "The network interface name is $ip_link_name"
        break
    fi
    sleep 5
    ip_show_retries=$((ip_show_retries+1))
done

if [ "X$ip_link_name" == "X" ]; then
    echo "ERROR: Failed to get the network interface name. The device might not be ready"
fi

ip_addr=$(ip -o -f inet addr show | grep -v 127.0.0.1 | awk '{print $4}')
if [ "X$ip_addr" == "X" ] && [ "X$ip_link_name" != "X" ]; then
    echo "Network interface $ip_link_name has no DHCP IPv4 address. Try to bring it up now ..."
    ip link set $ip_link_name up
    sleep 5
    ip_addr=$(ip -o -f inet addr show $ip_link_name | awk '{print $4}')
fi

echo "{{ autoinstall_ipv4_msg }}$ip_addr"
if [ "X$ip_addr" == "X" ]; then
    echo "ERROR: Failed to obtain DHCP IPv4 address"
fi

# Get display manager and config file
if [ -f /etc/systemd/system/display-manager.service ]; then
    OS_DM=$(readlink /etc/systemd/system/display-manager.service | awk -F '/' '{print $NF}' | awk -F '.' '{print $0}')
    if [[ "X$OS_DM" =~ Xgdm ]]; then
        echo "$OS_NAME $VERSION_ID display manager is GNOME"
        # Display manager config file
        if [ "X$OS_ID" == "Xdebian" ]; then
            OS_DM_CONF=/etc/gdm3/daemon.conf
        elif [ "X$OS_ID" == "Xubuntu" ]; then
            OS_DM_CONF=/etc/gdm3/custom.conf
        else
            OS_DM_CONF=/etc/gdm/custom.conf
        fi
    elif [[ "$OS_DM" =~ lightdm ]]; then
        OS_DM_CONF=/etc/lightdm/lightdm.conf
    fi

    if [ "X$OS_DM_CONF" != "X" ] && [ ! -e "$OS_DM_CONF" ]; then
      echo "ERROR: $OS_DM_CONF doesn't exist. Please check the config file for $OS_DM"
      OS_DM_CONF=""
    fi
fi
