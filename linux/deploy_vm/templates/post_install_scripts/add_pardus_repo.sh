# Comment out CDROM repo so apt update does not fail on missing CDROM
sed -i 's/^[[:blank:]]*deb cdrom:/# deb cdrom:/' /etc/apt/sources.list

# Configure APT to ignore SSL certificate validation for HTTPS mirrors/proxies and retry downloads
mkdir -p /etc/apt/apt.conf.d
cat << 'EOF' > /etc/apt/apt.conf.d/99ssl-insecure
Acquire::https::Verify-Peer "false";
Acquire::https::Verify-Host "false";
Acquire::Retries "3";
Acquire::ForceIPv4 "true";
EOF

# Replace depo.pardus.org.tr with direct mirror bilgemdepo.pardus.org.tr to avoid
# Mirrorbits 302 redirects to flaky/unreachable university mirrors (itu/deu/ktu)
sed -i 's/depo\.pardus\.org\.tr/bilgemdepo.pardus.org.tr/g' /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2>/dev/null || true

# Check and add official Pardus repos if they are not already configured
check_and_add_repo() {
    local repo_pattern="$1"
    local repo_line="$2"

    if ! grep -rqE "$repo_pattern" /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null; then
        echo "$repo_line" >> /etc/apt/sources.list
    fi
}

MAJOR_VERSION=$(echo $VERSION_ID | tr -d '"' | cut -d '.' -f 1)
if [ $MAJOR_VERSION -ge 23 ]; then
    check_and_add_repo "^[[:blank:]]*deb[[:blank:]]+[^#]*pardus\.org\.tr/pardus[[:blank:]]+${VERSION_CODENAME}([[:blank:]]|$)" \
        "deb http://bilgemdepo.pardus.org.tr/pardus $VERSION_CODENAME main contrib non-free non-free-firmware"

    check_and_add_repo "^[[:blank:]]*deb[[:blank:]]+[^#]*pardus\.org\.tr/pardus[[:blank:]]+${VERSION_CODENAME}-deb([[:blank:]]|$)" \
        "deb http://bilgemdepo.pardus.org.tr/pardus ${VERSION_CODENAME}-deb main contrib non-free non-free-firmware"

    check_and_add_repo "^[[:blank:]]*deb[[:blank:]]+[^#]*pardus\.org\.tr/guvenlik[[:blank:]]+${VERSION_CODENAME}-deb([[:blank:]]|$)" \
        "deb http://bilgemdepo.pardus.org.tr/guvenlik ${VERSION_CODENAME}-deb main contrib non-free non-free-firmware"
else
    check_and_add_repo "^[[:blank:]]*deb[[:blank:]]+[^#]*pardus\.org\.tr/pardus[[:blank:]]+${VERSION_CODENAME}([[:blank:]]|$)" \
        "deb http://bilgemdepo.pardus.org.tr/pardus $VERSION_CODENAME main contrib non-free"

    check_and_add_repo "^[[:blank:]]*deb[[:blank:]]+[^#]*pardus\.org\.tr/guvenlik[[:blank:]]+${VERSION_CODENAME}([[:blank:]]|$)" \
        "deb http://bilgemdepo.pardus.org.tr/guvenlik $VERSION_CODENAME main contrib non-free"
fi
