# Known issues
There are some known issues about Ansible VMware modules used in this project, VMware tools, or guest OS. Please file an issue to this project when you hit any failure in the testing but not listed here.

## Ansible modules
1. community.vmware.vmware_deploy_ovf
* Failure: Router VM deployment will fail if there are more than one standalone ESXi hosts in the same datacenter. 
* Issue link: https://github.com/ansible-collections/community.vmware/issues/670
* Workaround: Please install the community.vmware collection containing the fix, or comment out below 4 test cases in gosv_testcase_list.yml.
* Affected test cases:
```
network_device_ops/e1000e_network_device_ops.yml
network_device_ops/vmxnet3_network_device_ops.yml
guest_customization/gosc_perl_staticip.yml
guest_customization/gosc_cloudinit_staticip.yml
```

2. community.vmware module
* Failure: VMware module will fail with error 'virtual machine has already been deleted or has not been completely created' due to one VM is deleted while executing find VM in datacenter, e.g., vmware_vm_shell module.    
* Issue link: https://github.com/ansible-collections/community.vmware/issues/732
* Workaround: Please wait for the fix, or make sure not deleting VMs while the test is running.
* Affected test cases: Testing will fail if any of the task failed due to this issue.

## VMware tools
1. open-vm-tools 11.1.0 and later
* Failure: Below error log in '/var/log/vmware-imc/toolsDeployPkg.log' might cause guest OS reboot failure after Perl guest OS customization, and then lead to static IP configuration failure in RHEL/Oracle Linux/CentOS 7.x and 8.x,Alma Linux/Rocky Linux 8.x, SLES 15 SP2 and later, e.g.,
```
[   error] Process exited abnormally after 0 sec, uncaught signal 15
```
* Workaround: not available
* Affected test cases:
```
guest_customization/gosc_perl_staticip.yml
```

## Guest OS
1. Ubuntu 18.04 and later
* Failure: Configured DNS search domains in guest OS customization spec will not be set correctly in guest OS after cloud-init GOSC with DHCP network configuration.
* Workaround: not available
* Affected test cases:
```
guest_customization/gosc_cloudinit_dhcp.yml
```
2. SLE 15 SP2
* Failure: Get error when using 'zypper' module due to 'ImportError' when using Python2.
* Workaround: Set 'vm_python' parameter in 'vars/test.yml' to correct Python3 path, e.g., '/usr/bin/python3'.

* Failure: Get error 'A general system error occurred: vix error codes = (1, 4294967291).' while executing common/vm_shell_in_guest.yml.
* Workaround: Configure vmtoolsd to use common authentication mechanism using PAM. See https://kb.vmware.com/s/article/78251.

3. Windows 10 or Windows Server
* Failure: Get error when removing NVMe controller from VM with error message "The guest operating system did not respond to a hot-remove request for device nvme1 in a timely manner.".
* Workaround: not available
* Affected test cases:
```
vhba_hot_add_remove/nvme_vhba_device_ops.yml
```

4. VMware Photon OS 3.x
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

5. VMware Photon OS 4.0
* Failure: When hot adding or removing NVMe disk to existing controller, VMware Photon OS cannot detect NVMe disk changes.
* Workaround: not available
* Affected test cases:
```
vhba_hot_add_remove/nvme_vhba_device_ops.yml
```
