if [[ "X$OS_DM" =~ Xgdm ]]; then
    echo "Disable GNOME initial setup at first login"
    mkdir -p -m 755 /root/.config
    echo "yes" > /root/.config/gnome-initial-setup-done
    chown --recursive root:root /root/.config
{% if new_user is defined and new_user != 'root' %}
    mkdir -p -m 755 /home/{{ new_user }}/.config
    echo "yes" > /home/{{ new_user }}/.config/gnome-initial-setup-done
    chown --recursive {{ new_user }}:{{ new_user }} /home/{{ new_user }}/.config
{% endif %}
elif [[ "X$OS_DM" =~ Xlightdm ]]; then
    echo "TBD: Disable XFCE greeter at first login"
fi