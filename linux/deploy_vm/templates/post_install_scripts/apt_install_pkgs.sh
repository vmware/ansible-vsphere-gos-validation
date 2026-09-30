#Install open-vm-toools from CDROM if it exists
cdrom_missing_pkgs=""
for pkg in $required_pkgs; do
    echo "Searching package $pkg in CDROM"
    apt list $pkg 2>/dev/null | cut -d '/' -f 1 | grep $pkg
    pkg_in_cdrom=$?
    if [ $pkg_in_cdrom -eq 0 ]; then
        echo "Installing pacakge $pkg from CDROM"
        apt install -y $pkg 2>&1
        if [ $? -ne 0 ]; then
            echo "ERROR: Failed to install package $pkg from CDROM"
            cdrom_missing_pkgs="$cdrom_missing_pkgs $pkg"
        fi
    else
        echo "Package $pkg doesn't exist in CDROM"
        cdrom_missing_pkgs="$cdrom_missing_pkgs $pkg"
    fi
done

if [ "X$cdrom_missing_pkgs" != "X" ]; then
    echo "Adding $OS_NAME $VERSION_ID ($VERSION_CODENAME) offical online repo"
{% if unattend_installer == 'Debian' %}
    echo "deb http://deb.debian.org/debian/ $VERSION_CODENAME main contrib" >> /etc/apt/sources.list
{% elif unattend_installer == 'Pardus' %}
    {% include 'add_pardus_repo.sh' %}
{% endif %}

    echo "APT source list with online repos:"
    cat /etc/apt/sources.list

    echo "Updating list of available packages"
    apt update -y 2>&1

    for pkg in $cdrom_missing_pkgs; do
        echo "Searching package $pkg in online repo"
        apt list $pkg 2>/dev/null | cut -d '/' -f 1 | grep $pkg
        pkg_in_online_repo=$?
        if [ $pkg_in_online_repo -eq 0 ]; then
            echo "Installing package $pkg from online repo"
            apt install -y $pkg 2>&1
            if [ $? -ne 0 ]; then
                echo "ERROR: Failed to install package $pkg from online repo"
            fi
        else
            echo "ERROR: Failed to find package $pkg from CDROM and online repo"
        fi
    done
fi