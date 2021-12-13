# How to Create a Windows OVF Template

## Description
A new Windows VM will be deployed on your configured vCenter or ESXi host, after guest OS installed automatically using Autounattend.xml, specified VMware tools will be installed, then this VM will be exported to an OVF template saved in the specified path on your local machine.
* Configuration file: vars/create_windows_template_vars.yml
* Windows template creation playbook list file: windows/create_template_playbook_list.yml
* Windows Autounattend file path: autoinstall/Windows/,
  or you can put your customized Autounattend file into this path and configure it in file 'vars/export_windows_template_vars.yml' using variable 'unattend_install_conf'.
* VM user name and password for Windows client is 'test/B1gd3m0z', for Windows Server is 'Administrator/B1gd3m0z', which are hardcoded in Autounattend.xml files in this path 'autoinstall/Windows/'.

## Steps to Launch the Windows Template Creation
1. Copy the Windows ISO image to the datastore of ESXi host, on which you want to deploy a new virtual machine.
2. Set the infomation of vCenter server or ESXi host, the VM guest ID, VM configurations, Windows ISO image path, unattend xml file path, template destination path in file 'vars/export_windows_template_vars.yml'. 
3. Go to the path of 'main.yml' file, execute it with below command:
```
ansible-playbook main.yml -e "testing_vars_file=/absolute_path/vars/create_windows_template_vars.yml testing_testcase_file=/absolute_path/windows/create_template_playbook_list.yml"
```
4. VM OVF template will be exported to the path configured as 'exported_template_path' parameter, default is '/tmp/' when the playbook completed successfully.
5. Please refer to 'results.log' and 'failed_tasks.log' files in 'logs' folder for debugging.
