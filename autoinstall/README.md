# Unattend Automatic Install Config Files
1. For CentOS 7.x unattend auto-install, please use files under CentOS/7 or RHEL/7.
2. For RHEL or RHEL-like varieties 7.x unattend auto-install, please use files under RHEL/7.
3. For RHEL or RHEL-like varieties 8.x or later unattend auto-install, please use files under RHEL/8.
4. For SLES 15 SP3 or later unattend auto-install, please use files under SLE/15/SP3/SLES or SLE/15/SP3/SLES_Minimal.
5. For SLED 15 SP3 unattend auto-install, please use SLE/15/SP3/SLED/autoinst.xml.
6. For SLED 15 SP4 or later unattend auto-install, please use SLE/15/SP4/SLED/autoinst.xml.
7. For Windows 10, or Windows 11 with TPM device unattend auto-install, please use files under Windows/win10.
8. For Windows 11 without TPM device unattend auto-install, please use files under Windows/win11 to bypass TPM check during installation.
9. For Windows Server LTSC unattend auto-install, please use files under Windows/win_server.
10. For Windows Server SAC unattend auto-install, please use files under Windows/win_server_sac.
11. For Photon OS 3.0 or later unattend auto-install, please use file Photon/ks.cfg.
12. For Ubuntu Server 20.04 or later unattend auto-install, please use file Ubuntu/Server/user-data.j2.
13. For Ubuntu Desktop 20.04 ~ 22.10 unattend auto-install, please use file Ubuntu/Desktop/Ubiquity/ubuntu.seed.
14. For Ubuntu Destkop 23.04 or later unattend auto-install, please use file Ubuntu/Desktop/Subiquity/user-data.j2.
15. For Debian 10.1x, 11.x or later unattend auto-install, please use file Debian/10/preseed.cfg.
16. For UnionTech OS Server 20 1050a unattend auto-install, please use file UOS/Server/20/1050a/ks.cfg.
17. For UnionTech OS Server 20 1050e unattend auto-install, please use file UOS/Server/20/1050e/ks.cfg.
18. For Fedora Server 36 or later unattend auto-install, please use file Fedora/36/Server/ks.cfg.
19. For FreeBSD 13 unattend auto-install, please use file FreeBSD/13/installerconfig.
20. For FreeBSD 14 or later unattend auto-install, please use file FreeBSD/14/installerconfig.
21. For Pardus 21.2 Server and XFCE Desktop or later unattend auto-install, please use file Pardus/preseed.cfg.
22. For openSUSE Leap 15.3 or later unattend auto-install, please use file openSUSE/15/autoinst.xml.
23. For BCLinux 8.x unattend auto-install, please use file BCLinux/8/ks.cfg.
24. For BCLinux-for-Euler 21.10 unattend auto-install, please use file BCLinux-for-Euler/21.10/ks.cfg.
25. For FusionOS unattend auto-install, please use files under Fusion.

# Notes
## For Windows
1. If the OS auto install process does not proceed as expected or VM console shows error,
please try to set parameter "windows_product_key" in "vars/test.yml" file with the valid
license key and try again.
Also can refer to [Windows KMS Client Setup Key](https://docs.microsoft.com/en-us/windows-server/get-started/kmsclientkeys)
