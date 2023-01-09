# Common Task Usage

## VM related tasks
### Tasks for getting VM facts
* vm_get_id.yml: Get VM ID from ESXi host by vmware_guest_info module
* vm_get_guest_facts.yml: Gather info about a VM
* vm_get_guest_info.yml: Gather guest info of VM
* vm_get_config.yml: Get specified property of VM
* vm_get_power_state.yml: Get VM power status
* get_guest_system_info.yml: Get guest system info
* vm_get_device_with_key.yml: Get VM device with a specific key
* vm_get_device_with_label.yml: Get VM device with a specific label
* vm_get_video_card.yml: Get VM video card settings
* vm_get_cdrom_devices.yml: Get VM CDROM devices info list
* vm_get_vbs_status.yml: Get Windows VM VBS enablement status
* collect_ovf_vm_config.yml: Collect VM hardware configurations and save to a json file

### Tasks for VM deploy or remove
* vm_create.yml: Create a new VM on ESXi host
* vm_create_with_ide_disk.yml: Create a new VM which boot from an IDE disk on ESXi host
* ovf_deploy.yml: Deploy OVF template to VM
* ovf_export.yml: Export VM to OVF template
* vm_remove.yml: Delete VM from ESXi host
* vm_instant_clone.yml: Create an instant clone of VM

### Tasks for VM basic settings
* vm_set_guest_id.yml: Set VM's guest id
* vm_upgrade_hardware_version.yml: Upgrade VM's hardware version
* vm_configure_cdrom.yml: Configure VM's CDROM
* vm_guest_send_key.yml: Send key strokes to VM console
* vm_connect_cdrom_to_iso.yml: Connect VM's CDROM to an ISO file
* vm_set_power_state.yml: Set VM power state
* vm_wait_gosc_completed.yml: Wait for GOSC being completed
* vm_add_serial_port.yml: Add a serial port to VM
* vm_set_video_card.yml: Configure VM video card settings
* vm_remove_serial_port.yml: Remove a serial port from VM
* vm_add_remove_vtpm.yml: Add or remove vTPM device from VM
* vm_add_vtpm_device.yml: Add key provider on vCenter then add new vTPM device to VM
* vm_answer_question.yml: Answer question at VM power on

### Tasks for VM CPU or Memory settings
* vm_enable_cpu_hotadd.yml: Enable VM CPU hotadd
* vm_set_cpu_number.yml: Set VM CPU number, cores per socket is 1 by default
* vm_enable_memory_hotadd.yml: Enable VM memory hotadd
* vm_set_memory_size.yml: Set VM memory size in MB
* vm_set_nested_virtual.yml: Set if CPU virtualization can be exposed to the guest operating system

### Tasks for VM network settings
* vm_add_network_adapter.yml: Add a new network adapter to VM
* vm_remove_network_adapter.yml: Remove network adapter from VM
* vm_configure_network_adapter.yml: Reconfig VM network adapter connection settings
* vm_wait_network_connected.yml: Wait for network adapter to be connected
* vm_test_nic.yml: Check if given network adapter is connectable through ssh
* vm_get_network_facts.yml: Get VM network adapters info
* vm_get_netadapter_number.yml: Get VM network adapters number with different types

### Tasks for VM disk settings
* vm_hot_add_remove_disk_ctrl.yml: Hotadd or remove VM disk controller
* vm_hot_add_remove_disk.yml: Hotadd or remove VM disk
* vm_get_new_vhba_bus_number.yml: Get bus number of a new disk controller
* vm_get_new_disk_node_info.yml: Get disk node info of a new disk
* vm_get_disk_facts.yml: Get VM disk info
* vm_get_disk_controller_facts.yml: Get VM disk controller info
* vm_get_disk_controller_num.yml: Get VM disk controller number with specified type
* vm_add_sata_cdrom.yml: Add a new CDROM attached to SATA controller

### Tasks for VM secureboot settings
* vm_set_boot_options.yml: Set VM boot configurations
* vm_get_boot_info.yml: Get VM boot configurations

### Tasks for VM snapshots or screenshot
* vm_get_snapshot_facts.yml: Get VM's snapshot facts
* vm_remove_snapshot.yml: Remove VM's snapshot
* vm_revert_snapshot.yml: Revert to snapshot on VM
* vm_take_snapshot.yml: Take snapshot on VM
* vm_cleanup_snapshot.yml: Revert to specified snapshot and then remove all snapshots
* vm_check_snapshot_exist.yml: Check if specified snapshot exists
* vm_rename_snapshot.yml: Rename an existing snapshot
* vm_take_screenshot.yml: Take VM console screenshot
* vm_wait_expected_snapshot.yml: Wait current snapshot is the expected one

### Tasks for getting VM IP
* vm_get_ip.yml: Get VM IP address by calling vm_get_ip_from_vmtools.yml
* vm_get_ip_from_vmtools.yml: Get VM IP address from VMware tools guestinfo
* vm_get_primary_nic.yml: Get VM connectable network adapter MAC/IP address
* vm_get_ip_from_notools.yml: Get VM IP address when there is no VMware tools installed
* vm_get_world_id.yml: Get VM world ID on ESXi host
* vm_get_ip_esxcli.yml: Get VM IP address on ESXi host by esxcli command
* update_inventory.yml: Get VM IP address again or update the in memory hosts inventory info

### Tasks for VM information from command line
* vm_shell_in_guest.yml: Execute shell command in guest
* vm_guest_file_operation.yml: Create/delete directory or fetch/copy files in guest with VMware tools installed

### Tasks for VM log files
* vm_wait_log_msg.yml: Check or wait for a message appear in VM's log file

### Tasks for VM vmx config
* vm_get_extra_config.yml: Get all configs in the vmx file
* vm_set_extra_config.yml: Set VM config in the vmx file
* vm_get_vm_info.yml: Get VM datastore path, VM files path, VM guest ID, hardware version info

### Tasks for VM connection
* vm_wait_connection.yml: Wait for VM is connectable via ping and ssh
* vm_wait_ssh.yml: Wait for port 22 to be open for connect and get specified keyword
* vm_wait_ping.yml: Wait for VM is connectable via ping
* vm_wait_guest_ip.yml: Wait for guest IP addresses in guest info
* vm_wait_guest_fullname.yml: Wait for VMware tools collecting guest fullname
* vm_wait_guest_hostname.yml: Wait for VMware tools collecting guest OS hostname

### Tasks for VMware Tools
* vm_get_vmtools_status.yml: Get VMware Tools status, version, release and build information
* vm_wait_vmtools_status: Wait for VMware Tools is in expected status

## ESXi/vCenter server related tasks
### Tasks for features on ESXi
* esxi_enable_guest_ip_hack.yml: Enable guest IP hack on ESXi host
* esxi_get_property.yml: Get specified property of ESXi host
* esxi_get_bundled_tools_path.yml: Get the bundled VMware tools path on ESXi host
* esxi_get_hardware_versions.yml: Get supported hardware versions and default hardware version on ESXi host
* esxi_get_guest_ids.yml: Get supported guest ids for a hardware version on ESXi host
* esxi_get_guest_config_options.yml: Get VM config options for a guest id on a hardware version
* esxi_get_pmem_info.yml: Get ESXi host total and available persistent memroy size in MB
* esxi_set_advanced_system_settings.yml: Configure ESXi host's advanced system settings
* esxi_get_advanced_system_settings.yml: Get ESXi host's advanced system settings
* esxi_get_vmkernel_adapters.yml: Get ESXi host's VMkernel network adapters
* esxi_get_new_vmkernel_adapter.yml: Get index and name of a new VMkernel network adapter on ESXi host
* esxi_manage_vmkernel_adapter.yml: Add or remove a VMkernel network adapter on ESXi host
* esxi_set_firewall_rule.yml: Enable or disable a firewall rule on ESXi host
* esxi_enable_pvrdma_configs.yml: Tag VMkernel network adapter and enable firewall rule on ESXi host for PVRDMA communication
* esxi_disable_pvrdma_configs.yml: Remove VMkernel network adapter tag and disable firewall rule on ESXi host for PVRDMA communication

### Tasks for ESXi datastores
* esxi_add_datastore.yml: Add NFS or VMFS datastore to ESXi host
* esxi_get_datastores.yml: Get ESXi server datastores info
* esxi_get_datastore_info.yml: Get specified datastore info on ESXi server
* esxi_check_delete_datastore_file.yml: Get datastore file status or delete file
* esxi_upload_datastore_file.yml: Upload file to ESXi datastore
* esxi_download_datastore_file.yml: Download file from ESXi datastore
* vcenter_add_standard_kp.yml: Add Standard Key Provider on vCenter

### Tasks for server information
* esxi_get_host_facts.yml: Get ESXi server host facts
* esxi_get_vmnic_facts.yml: Get phyical NICs facts on ESXi server
* esxi_get_version_build.yml: Get ESXi release version and milestone
* vcenter_get_version_build.yml: Get vCenter server version info
* esxi_get_model.yml: Get ESXi server model and CPU model info

### Tasks for vSphere Standard Switch (VSS) and Port Group
* esxi_add_portgroup.yml: Add a new virtual switch port group
* esxi_remove_portgroup.yml: Remove a virtual switch port group
* esxi_get_portgroup_facts.yml: Get virtual switch port group facts
* esxi_wait_portgroup.yml: Wait for specified port group info retrieved
* esxi_add_vswitch.yml: Add a new vSphere Standard Switch
* esxi_remove_vswitch.yml: Remove a vSphere Standard Switch
* esxi_get_vswitch_facts.yml: Get virtual switch facts

### Tasks for vSphere Distributed Switch (VDS) and Port Group
* vcenter_manage_vds.yml: Create or remove a vSphere Distributed Switch
* vcenter_get_vds_info.yml: Gather information about a vSphere Distributed Switch
* vcenter_manage_vds_portgroup.yml: Create or remove a distributed port group on vCenter Server
* vcenter_manage_vds_host.yml: Add or remove an ESXi host for a vSphere Distributed Switch on vCenter Server

## Localhost tasks
### Tasks for NFS mount and unmount
* local_mount.yml: Mount device or NFS volume or something else to the path on localhost
* local_unmount.yml: Unmount device or NFS volume or something else from localhost
* delete_local_file.yml: Delete local file or directory
* mount_nfs_storage_local.yml: Mount NFS volume to the path on localhost

### Folder and file management
* create_iso.yml: Create an iso file
* create_temp_file_dir.yml: Craete a temporary file or directory under /tmp
* check_testcase_in_file.yml: Find if specified testcase in testcase list file
* transfer_file_remote.yml: Transfer file to specified remote host
* update_ini_style_file.yml: Update INI-style file content
* create_directory.yml: Create a new directory with specified path

## Testing related
* set_vmware_module_hostname.yml: Check and set configured vCenter or ESXi server info
* add_host_in_memory_inventory.yml: Add host to in memory hosts inventory
* router_vm_deploy.yml: Deploy a router VM for network testing or GOSC testing
* network_testbed_setup.yml: Setup network adapter testing testbed
* network_testbed_cleanup.yml: Cleanup network adapter testing testbed
* vds_network_setup.yml: Setup vSphere Distributed Switch networking
* vds_network_cleanup.yml: Cleanup vSphere Distributed Switch networking
* test_rescue: Tasks executed when test case failure
* skip_test_case.yml: Tasks for skipping testcase and ending play

## Common tasks for Linux and Windows test cases
* compose_vm_cdroms.yml: Generate VM CDROM device info list for creating new VM
* download_iso_and_transfer.yml: Download ISO file and transfer to ESXi datastore
* get_iso_file_list.yml: Generate and validate OS installation ISO file list
