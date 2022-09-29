# Guest OS Validation on vSphere using Ansible

## Getting Started

### Prerequisites
1. Install Ansible on your control machine, please refer to [Installing Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)
2. Install required Python libraries in requirements.txt
```
$ pip install -r requirements.txt
```
3. Install required Ansible collections in requirements.yml
```
$ ansible-galaxy install -r requirements.yml
```
4. To test VMware Photon OS, Debian, and Ubuntu with ISO installation, it is also required to install `xorriso` package on your control machine.
5. Log in to local control machine as root or a user in sudoers

### Steps to Launch Testing
1. Git clone project from github to your workspace on control machine,
2. Set the parameters required for testing in this file: vars/test.yml,
3. Modify the test cases in test case list file in below default path,
   * For Linux testing: linux/gosv_testcase_list.yml
   * For Windows testing: windows/gosv_testcase_list.yml
4. Launch testing using below commands from the same path of "main.yml",
```
  # For Linux testing:
  # you can use below command to use the default variables file "vars/test.yml",
  # default test case list file "linux/gosv_testcase_list.yml"
  $ ansible-playbook main.yml

  # For Linux or Windows testing:
  # you can use below command to set the path of a customized variables file and
  # test case list file
  $ ansible-playbook main.yml -e "testing_vars_file=/path_to/test.yml testing_testcase_file=/path_to/gosv_testcase_list.yml"
```
5. New folder for log files and files collected in test cases are created for current test run,
e.g., "logs/test-vm/2021-07-06-09-27-51/",
find test case results in "results.log", failed tasks in "failed_tasks.log", testing debug log in "full_debug.log". 

### Catalog
* main.yml: Main playbook for Guest OS validation test
* ansible.cfg: User customized Ansible configuration file
* autoinstall: Folder for guest OS unattend install configuration files
* common: Folder for common tasks called in test cases
* docs: Folder for guide file and known issues
* env_setup: Folder for playbooks or tasks which to prepare or cleanup testing environment
* linux: Folder for playbooks to test Linux guest OS
* windows: Folder for playbooks to test Windows guest OS
* plugin: Folder for plugin scripts
* tools: Folder for 3rd-party tools used in test cases
* vars: Folder for variable files used in testing
* changelogs: Folder for changelog of each release 

### Supported Testing Scenarios
This project supports below scenarios for end-to-end guest OS validation testing 
* Deploy VM and install guest OS from ISO image
* Deploy VM from an OVA template
* Existing VM with installed guest OS, which should satisfy below requirments.
  * SSH and Python are installed and enabled
  * The vm_python variable in vars/test.yml must be set with correct python path. Or user can set PATH in /etc/environment in guest OS to include the binary directory path to python.
  * The root user should be enabled and permitted to log in through SSH in Linux guest OS
  * Execute [ConfigureRemotingForAnsible.ps1](https://github.com/ansible/ansible/blob/devel/examples/scripts/ConfigureRemotingForAnsible.ps1) script in Windows guest OS in advance

### Supported Guest OS

| Guest OS types/versions                         | Automatic install from ISO image | Deploy from ova template | Existing VM and installed guest OS |
| :---------------------------------------------- | :------------------------------: | :----------------------: | :--------------------------------: |
| Red Hat Enterprise Linux 7.x, 8.x, 9.x          | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| CentOS 7.x, 8.x                                 | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| Oracle Linux 7.x, 8.x, 9.0                      | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| Rocky Linux 8.x, 9.0                            | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| AlmaLinux 8.x, 9.0                              | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| SUSE Linux Enterprise 15 SP3 and later          | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| SUSE Linux Enterprise 12 SP5, 15 SP0/SP1/SP2    |                                  |                          | :heavy_check_mark:                 |
| Photon OS 3.x, 4.x                              | :heavy_check_mark:               | :heavy_check_mark:       | :heavy_check_mark:                 |
| Ubuntu 18.04 and later live-server              | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| Ubuntu 20.04 and later cloud image              |                                  | :heavy_check_mark:       | :heavy_check_mark:                 |
| Ubuntu 18.04 and later desktop                  |                                  |                          | :heavy_check_mark:                 |
| Flatcar 2592.0.0 and later                      |                                  | :heavy_check_mark:       | :heavy_check_mark:                 |
| Debian 10.10 and later, 11.x                    | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| Debian 9.x, 10.9 and earlier                    |                                  |                          | :heavy_check_mark:                 |
| Windows 10, 11                                  | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| Windows Server 2019, 2022                       | :heavy_check_mark:               |                          | :heavy_check_mark:                 |

Note: This supported guest OS list is used for this project only. For guest OS support status on ESXi, please refer to [VMware Compatibility Guide](https://www.vmware.com/resources/compatibility/search.php?deviceCategory=software&testConfig=16).

### Docker images
* Latest (Release v2.1):
  * projects.registry.vmware.com/gos_cert/ansible-vsphere-gos-validation:latest
* Release v2.1:
  * projects.registry.vmware.com/gos_cert/ansible-vsphere-gos-validation:v2.1

Launch testing using Docker image
1. Execute below commands in your machine
```
$ docker pull projects.registry.vmware.com/gos_cert/ansible-vsphere-gos-validation:latest
$ docker run -it --privileged projects.registry.vmware.com/gos_cert/ansible-vsphere-gos-validation:latest
```
2. Launch testing in the started container following the steps in this section [Steps to Launch Testing](#steps-to-launch-testing)
