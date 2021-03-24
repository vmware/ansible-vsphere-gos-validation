# Launch the sample testing
This sample will download a CentOS iso from specific url, creat VM as below and install the CentOS onto the VM, and then run test cases on it.
* VM name: CentOS_79_ansible_vsphere_gosv
* VM guest ID: centos7_64Guest
* VM user name and password: root/B1gd3m0z

Steps:
1. Fill the vCenter server and ESXi host information, and the absolute path of 'test.yml' file in the current sample folder in 'test_env.yml',
2. (Optional) Change the test cases to be executed in this file 'linux/gosv_testcase_list.yml',
3. Execute main.yml playbook from the root path of this project,
```
ansible-playbook main.yml -e "@sample/test_env.yml"
```
4. 'results.log' and other log files will be generated in 'logs/CentOS_79_ansible_vsphere_gosv/xxxxx/'.
