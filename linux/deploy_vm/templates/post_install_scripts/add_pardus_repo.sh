# Check and add official Pardus repos if they are not already configured
check_and_add_repo() {
    local repo_pattern="$1"
    local repo_line="$2"
    local repo_found=0

    if [ -f /etc/apt/sources.list ] && grep -qE "$repo_pattern" /etc/apt/sources.list 2>/dev/null; then
        repo_found=1
    elif [ -d /etc/apt/sources.list.d ]; then
        for f in /etc/apt/sources.list.d/*.list; do
            if [ -f "$f" ] && grep -qE "$repo_pattern" "$f" 2>/dev/null; then
                repo_found=1
                break
            fi
        done
    fi

    if [ $repo_found -eq 0 ]; then
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