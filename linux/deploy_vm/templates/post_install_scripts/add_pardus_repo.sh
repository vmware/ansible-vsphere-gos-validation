MAJOR_VERSION=$(echo $VERSION_ID | cut -d '.' -f 1)
if [ $MAJOR_VERSION -ge 23 ]; then
    echo "deb http://depo.pardus.org.tr/pardus $VERSION_CODENAME main contrib non-free non-free-firmware" >> /etc/apt/sources.list
    echo "deb http://depo.pardus.org.tr/pardus ${VERSION_CODENAME}-deb main contrib non-free non-free-firmware" >> /etc/apt/sources.list
    echo "deb http://depo.pardus.org.tr/guvenlik ${VERSION_CODENAME}-deb main contrib non-free non-free-firmware" >> /etc/apt/sources.list
else
    echo "deb http://depo.pardus.org.tr/pardus $VERSION_CODENAME main contrib non-free" >> /etc/apt/sources.list
    echo "deb http://depo.pardus.org.tr/guvenlik $VERSION_CODENAME main contrib non-free" >> /etc/apt/sources.list
fi;