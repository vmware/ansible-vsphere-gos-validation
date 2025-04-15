# Unattend Automatic Install Config Files
- For CentOS 7.x unattend auto-install, please use files under CentOS/7 or RHEL/7.
- For CentOS Stream 8 or later unattend auto-install, please use files under RHEL/8.
- For RHEL or RHEL-like varieties 7.x unattend auto-install, please use files under RHEL/7.
- For RHEL or RHEL-like varieties 8.x or later unattend auto-install, please use files under RHEL/8.
- For SLED 15 SP3 unattend auto-install, please use file SLE/15/SP3/SLED/autoinst.xml.
- For SLED 15 SP4 or later unattend auto-install, please use file SLE/15/SP4/SLED/autoinst.xml.
- For SLES 15 SP3 or later unattend auto-install, please use files under SLE/15/SP3/SLES or SLE/15/SP3/SLES_Minimal.
- For SLES 16.0 unattend auto-install, please use file SLE/16.0/SLES/autoinst.jsonnet.
- For Windows 10, or Windows 11 with TPM device unattend auto-install, please use files under Windows/win10.
- For Windows 11 without TPM device unattend auto-install, please use files under Windows/win11 to bypass TPM check during installation.
- For Windows Server LTSC releases unattend auto-install, please use files under Windows/win_server.
- For Windows Server AC releases unattend auto-install, please use files under Windows/win_server_ac.
- For Photon OS 3.0 or later unattend auto-install, please use file Photon/ks.cfg.
- For Ubuntu Server 20.04 or later unattend auto-install, please use file Ubuntu/Server/user-data.j2.
- For Ubuntu Desktop 20.04 ~ 22.10 unattend auto-install, please use file Ubuntu/Desktop/Ubiquity/ubuntu.seed.
- For Ubuntu Destkop 23.04 or later unattend auto-install, please use file Ubuntu/Desktop/Subiquity/user-data.j2.
- For Debian 10.1x, 11.x or later unattend auto-install, please use file Debian/10/preseed.cfg.
- For UnionTech OS Server 20 1050a unattend auto-install, please use file UOS/Server/20/1050a/ks.cfg.
- For UnionTech OS Server 20 1050e unattend auto-install, please use file UOS/Server/20/1050e/ks.cfg.
- For Fedora 36 Server and Workstation or later unattend auto-install, please use files under Fedora/36.
- For FreeBSD 13 unattend auto-install, please use file FreeBSD/13/installerconfig.
- For FreeBSD 14 or later unattend auto-install, please use file FreeBSD/14/installerconfig.
- For Pardus 21.2 Server and XFCE Desktop or later unattend auto-install, please use file Pardus/preseed.cfg.
- For Pardus 23.x Server and XFCE Desktop unattend auto-install, please use file Pardus/preseed.cfg.
- For openSUSE Leap 15.3 or later unattend auto-install, please use file openSUSE/15/autoinst.xml.
- For openSUSE Leap 16.0 unattend auto-install, please use file openSUSE/16.0/autoinst.jsonnet.
- For BCLinux 8.x unattend auto-install, please use file BCLinux/8/ks.cfg.
- For BCLinux-for-Euler 21.10 unattend auto-install, please use file BCLinux-for-Euler/21.10/ks.cfg.
- For FusionOS 22 unattend auto-install, please use files under Fusion.
- For FusionOS 23 unattend auto-install, please use file Fusion/server_without_GUI/ks.cfg.
- For Kylin Linux Advanced Server V10 unattend auto-install, please use file Kylin/Server/10/ks.cfg.

# Notes
## For Windows
1. If the OS auto install process does not proceed as expected or VM console shows error,
please try to set parameter "windows_product_key" in "vars/test.yml" file with the valid
license key and try again.
Also can refer to [Windows KMS Client Setup Key](https://docs.microsoft.com/en-us/windows-server/get-started/kmsclientkeys)
