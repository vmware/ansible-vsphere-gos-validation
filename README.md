# Guest Operating System Validation on vSphere using Ansible

## Getting Started

### Prerequisites
1. Install Ansible on your control machine, please refer to [Installing Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)
2. Install required Python libraries in requirements.txt
```
$ pip install -r requirements.txt
```
3. Install required Ansible collections with latest version in requirements.yml
```
$ ansible-galaxy install -r requirements.yml
```
4. Log in to local control machine as root or a user in sudoers

### Steps to Launch Testing
1. Git clone project from github to your workspace on control machine.
2. Set the parameters required for testing in this file: `vars/test.yml`.
3. Modify the test cases in test case list file in below default path.
   * For Linux testing: `linux/gosv_testcase_list.yml`
   * For Windows testing: `windows/gosv_testcase_list.yml`
4. Launch testing using below commands from the same path of `main.yml`.
```
  # For Linux testing:
  # you can use below command to use the default variables file "vars/test.yml",
  # and default test case list file "linux/gosv_testcase_list.yml"
  $ ansible-playbook main.yml

  # For Linux or Windows testing:
  # you can use below command to set the path of a customized variables file and
  # test case list file
  $ ansible-playbook main.yml -e "testing_vars_file=/path_to/test.yml testing_testcase_file=/path_to/gosv_testcase_list.yml"
```
5. A new log folder will be created for current test run, which will include log files and files collected in test cases, e.g., `logs/test-vm/2021-07-06-09-27-51/`. You can find log files:
  * `results.log` which contains testbed information, VM information and test case results
  * `full_debug.log` which contains testing debug logs
  * `failed_tasks.log` which contains failed tasks logs
  * `known_issues.log` which lists known issues meet in current test run

### Catalog
* main.yml: Main playbook for guest operating system validation test
* ansible.cfg: User customized Ansible configuration file
* autoinstall: Folder for guest operating system unattend install configuration files
* common: Folder for common tasks called in test cases
* docs: Folder for guide file and known issues
* env_setup: Folder for playbooks or tasks which to prepare or cleanup testing environment
* linux: Folder for playbooks to test Linux guest operating system
* windows: Folder for playbooks to test Windows guest operating system
* plugin: Folder for plugin scripts
* tools: Folder for 3rd-party tools used in test cases
* vars: Folder for variable files used in testing
* changelogs: Folder for changelog of each release 

### Supported Testing Scenarios
This project supports below scenarios for end-to-end guest operating system validation testing 
* Deploy VM and install guest operating system from ISO image
* Deploy VM from an OVA template
* Existing VM with installed guest operating system, which should satisfy below requirments.
  * VM has only one network adapter and the network adapter is connected.
  * SSH and Python are installed and enabled.
  * The vm_python variable in vars/test.yml must be set with correct python path. Or user can set PATH in /etc/environment in guest operating system to include the binary directory path to python.
  * The root user should be enabled and permitted to log in through SSH in Linux guest operating system.
  * Execute [ConfigureRemotingForAnsible.ps1](https://github.com/ansible/ansible/blob/devel/examples/scripts/ConfigureRemotingForAnsible.ps1) script in Windows guest operating system in advance.

### Compatible Guest Operating Systems

| Guest Operating Systems                       | Automatic Install from ISO Image | Deploy from OVA Template | Existing VM with Guest Operating System Installed |
|:----------------------------------------------| :------------------------------: | :----------------------: | :--------------------------------: |
| Red Hat Enterprise Linux 7.x, 8.x, 9.x        | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| CentOS 7.x, 8.x                               | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| Oracle Linux 7.x, 8.x, 9.x                    | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| Rocky Linux 8.x, 9.x                          | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| AlmaLinux 8.x, 9.x                            | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| SUSE Linux Enterprise 15 SP3 and later        | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| SUSE Linux Enterprise 12 SP5, 15 SP0/SP1/SP2  |                                  |                          | :heavy_check_mark:                 |
| VMware Photon OS 3.0, 4.0, 5.0                | :heavy_check_mark:               | :heavy_check_mark:       | :heavy_check_mark:                 |
| Ubuntu 18.04 live-server                      | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| Ubuntu 18.04 desktop                          |                                  |                          | :heavy_check_mark:                 |
| Ubuntu 20.04 and later                        | :heavy_check_mark:               | :heavy_check_mark:       | :heavy_check_mark:                 |
| Flatcar 2592.0.0 and later                    |                                  | :heavy_check_mark:       | :heavy_check_mark:                 |
| Debian 10.10 and later, 11.x                  | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| Debian 9.x, 10.9 and earlier                  |                                  |                          | :heavy_check_mark:                 |
| Windows 10, 11                                | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| Windows Server 2019, 2022                     | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| UnionTech OS Server 20 1050a                  | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| Fedora Server 36 and later                    | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| ProLinux Server 7.9, 8.5                      | :heavy_check_mark:               |                          | :heavy_check_mark:                 |
| FreeBSD 13 and later (*)                      | :heavy_check_mark:               |                          |                                    |
| Pardus 21.2 Server,XFCE Desktop and later (*) | :heavy_check_mark:               |                          |                                   |
| openSUSE Leap 15.3 and later                  | :heavy_check_mark:               |                          | :heavy_check_mark:                 |

**Notes**
1. This compatible guest operating systems list is used for this project only. For guest operating system support status on ESXi, please refer to [VMware Compatibility Guide](https://www.vmware.com/resources/compatibility/search.php?deviceCategory=software&testConfig=16).
2. Guest OS marked with (*) only supports autoinstall and doesn't support end-to-end tests for now.

### Docker images
* Latest (Release v2.3):
  * projects.registry.vmware.com/gos_cert/ansible-vsphere-gos-validation:latest
* Release v2.3:
  * projects.registry.vmware.com/gos_cert/ansible-vsphere-gos-validation:v2.3

Launch testing using Docker image
1. Execute below commands in your machine
```
$ docker pull projects.registry.vmware.com/gos_cert/ansible-vsphere-gos-validation:latest
$ docker run -it --privileged projects.registry.vmware.com/gos_cert/ansible-vsphere-gos-validation:latest
```
2. Launch testing in the started container following the steps in this section [Steps to Launch Testing](#steps-to-launch-testing)
