# Check if official Pardus repos are already configured in /etc/apt/sources.list or /etc/apt/sources.list.d/
files_to_check="/etc/apt/sources.list"
if [ -d /etc/apt/sources.list.d ]; then
    files_to_check="$files_to_check /etc/apt/sources.list.d"
fi
if ! grep -rqE "^[[:blank:]]*deb[[:blank:]].*pardus\.org\.tr/(pardus|guvenlik)" $files_to_check 2>/dev/null; then
    MAJOR_VERSION=$(echo $VERSION_ID | tr -d '"' | cut -d '.' -f 1)
    if [ $MAJOR_VERSION -ge 23 ]; then
        echo "deb http://bilgemdepo.pardus.org.tr/pardus $VERSION_CODENAME main contrib non-free non-free-firmware" >> /etc/apt/sources.list
        echo "deb http://bilgemdepo.pardus.org.tr/pardus ${VERSION_CODENAME}-deb main contrib non-free non-free-firmware" >> /etc/apt/sources.list
        echo "deb http://bilgemdepo.pardus.org.tr/guvenlik ${VERSION_CODENAME}-deb main contrib non-free non-free-firmware" >> /etc/apt/sources.list
    else
        echo "deb http://bilgemdepo.pardus.org.tr/pardus $VERSION_CODENAME main contrib non-free" >> /etc/apt/sources.list
        echo "deb http://bilgemdepo.pardus.org.tr/guvenlik $VERSION_CODENAME main contrib non-free" >> /etc/apt/sources.list
    fi
fi