# Enable user auto login
if [[ "X$OS_DM" =~ Xgdm ]] && [[ "X$OS_DM_CONF" != "X" ]]; then
{% if new_user is defined and new_user != 'root' %}
    echo "Enable auto login for new user {{ new_user }}"
    sed -ri 's/#? *AutomaticLogin *=.*$/AutomaticLogin={{ new_user }}/' $OS_DM_CONF
{% else %}
    echo "Enable auto login for root"
    sed -ri 's/#? *AutomaticLogin *=.*$/AutomaticLogin=root/' $OS_DM_CONF
{% endif %}
    sed -ri 's/#? *AutomaticLoginEnable *=.*$/AutomaticLoginEnable=true/' $OS_DM_CONF
elif [[ "X$OS_DM" =~ Xlightdm ]] && [[ "X$OS_DM_CONF" != "X" ]]; then
{% if new_user is defined and new_user != 'root' %}
    echo "Enable auto login for new user {{ new_user }}"
    sed -ri 's/#autologin-user=/autologin-user={{ new_user }}/' $OS_DM_CONF
{% else %}
    echo "Enable auto login for root"
    sed -ri 's/#autologin-user=/autologin-user=root/' $OS_DM_CONF
{% endif %}
    sed -ri 's/#autologin-user-timeout=.*$/autologin-user-timeout=0/' $OS_DM_CONF
fi