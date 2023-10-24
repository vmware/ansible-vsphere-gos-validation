if [ -e /etc/default/locale ]; then
    echo "Set default locale to en_US.UTF-8"
    echo 'LC_ALL="en_US.UTF-8"' >> /etc/default/locale
fi
