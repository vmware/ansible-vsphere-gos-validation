# Known issues
There are some known issues about Ansible VMware modules used in this project, VMware tools, or guest OS. Please file an issue to this project when you hit any failure in the testing but not listed here.

## Guest OS
1. SLE 15 SP2
* Failure: Get error when using 'zypper' module due to 'ImportError' when using Python2.
* Workaround: Set 'vm_python' parameter in 'vars/test.yml' to correct Python3 path, e.g., '/usr/bin/python3'.

* Failure: Get error 'A general system error occurred: vix error codes = (1, 4294967291).' while executing common/vm_shell_in_guest.yml.
* Workaround: Configure vmtoolsd to use common authentication mechanism using PAM. See https://kb.vmware.com/s/article/78251.

2. Windows 10 or Windows Server
* Failure: Get error when removing NVMe controller from VM with error message "The guest operating system did not respond to a hot-remove request for device nvme1 in a timely manner.".
* Workaround: not available
* Affected test cases:
```
vhba_hot_add_remove/nvme_vhba_device_ops.yml
```

3. VMware Photon OS 3.x
* Failure: After reinstalling open-vm-tools 11.2.5, the VGAuthService cann't be started successfully due to xmlsec1 version mismatch
* Workaround: Manually upgrade xmlsec1 package by running command 'tdnf install xmlsec1', and then reboot Photon OS.
* Affected test cases:
```
vgauth_check_service/vgauth_check_service.yml
```

* Failure: Perl GOSC with open-vm-tools 11.1.0 would fail to set hostname and domain.
* Workaround: Upgrade open-vm-tools to latest version.
* Affected test cases:
```
guest_customization/gosc_cloudinit_dhcp.yml
guest_customization/gosc_cloudinit_staticip.yml
```

4. SLES 15 SP1 and later
* Failure: Perl GOSC would fail to customize DNS servers and search domains on vSphere 6.5 and 6.7. See https://kb.vmware.com/s/article/70682.
* Workaround: Upgrade vSphere to 6.5 U3, 6.7 U3 or 7.0 and later.
```
guest_customization/gosc_perl_dhcp.yml
guest_customization/gosc_perl_staticip.yml
```

5. Windows 11
* Failure: Guest customization test cases would fail with SYSPREP error "Package Microsoft.OneDriveSync_21180.905.7.0_neutral__8wekyb3d8bbwe was installed for a user, but not provisioned for all users. This package will not function properly in the sysprep image." due to the known Windows issue.
* Workaround: Uninstall OneDrive in guest OS.
```
guest_customization/gosc_sanity_staticip.yml
guest_customization/gosc_sanity_dhcp.yml
```
