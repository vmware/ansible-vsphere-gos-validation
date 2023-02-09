# Test case development guide

## Test case:
- Create a new folder in this path "linux/" with the name of test case for Linux, or in this path "windows/" for Windows test case, e.g., "linux/new_test_case/" or "windows/new_test_case/".
- Define test case required user configuration parameters in file "vars/test.yml", also add the description of how to configure it.
- Add and write test case playbook in test case folder, e.g., "linux/new_test_case/new_test_case.yml". 
- Add test case playbook file path to this test case list file "linux/gosv_testcase_list.yml" for Linux, or "windows/gosv_testcase_list.yml" for Windows after new added test case is ready.
- Use the common tasks for VM, ESXi, vCenter or localhost operations in "common/" folder, tasks executed in Linux guest OS are in "linux/utils/", tasks executed in Windows guest OS are in "windows/utils/".
- Add new common task to "common/", "linux/utils/" or "windows/utils/" if existing tasks cannot provide the required functionality.
- Put all other test case related tasks in the test case folder.

## Test case folder:
- One test case playbook.
- Test case related tasks.
- Test case required Apps or scripts.

### How to write test case playbook:
1. name
- Set the playbook 'name' to the same name as the playbook file or test case name.
2. hosts
- Set the playbook 'hosts' to "localhost", as tasks executed on local machine, when there are tasks need to be executed on remote VM or ESXi server, use "delegate_to" keyword on the task.
3. vars_files
- Set the playbook 'vars_files' to the relative path to the configuration file "vars/test.yml", and/or other required variables file.
4. tasks
- This part contains "block" and "rescue" sections, write all the tasks of test case execution and validation in "block" part, "rescue" part includes a common task "common/test_rescue.yml". It means any task fails in "block" part, the testing will jump to the "rescue" part to execute failure/error handling tasks.

Below is an example of test case playbook:
```
- name: new_test_case
  hosts: localhost
  vars_files:
    - "{{ testing_vars_file | default('../../vars/test.yml') }}"
  tasks:
    - name: "Test case block"
      block:
        - name: "Test setup"
          include_tasks: ../setup/test_setup.yml

        - name: "Skip test case"
          include_tasks: ../../common/skip_test_case.yml
          vars:
            skip_msg: "Skip test case '{{ ansible_play_name }}' due to VM config is not applicable for this test case."
            skip_reason: "Not Applicable"
          when: test_case_not_applicable | bool

        - name: "Skip test case"
          include_tasks: ../../common/skip_test_case.yml
          vars:
            skip_msg: "Skip test case '{{ ansible_play_name }}' due to guest OS not support this test case."
            skip_reason: "Not Supported"
          when: test_case_not_supported | bool

        - name: "Skip test case"
          include_tasks: ../../common/skip_test_case.yml
          vars:
            skip_msg: "Skip test case '{{ ansible_play_name }}' due to required VM or guest OS condition is not meet."
            skip_reason: "Blocked"
          when: not meet_test_case_dependency | bool

        - name: "Run testing"
          block:
            - name: "Do configurations and get results"
              include_tasks: new_test_case_task.yml
            
            - name: "Verify results"
              ansible.builtin.assert:
                that:
                  - task_result == expected_value
                fail_msg: "{{ test_result }} is not the expected one: {{ expected_value }}"
                success_msg: "{{ test_result }} is as expected: {{ expected_value }}"

          when:
            - not test_case_not_applicable | bool
            - not test_case_not_supported | bool
            - meet_test_case_dependency | bool
      rescue:
        - name: "Test case failure"
          include_tasks: ../../common/test_rescue.yml
```

#### Test case "block"
1. In the "block" part, the first included task is "setup/test_setup.yml", will fulfill below functions mainly:
* check base snapshot existence status, revert to it if it exists,
* if base snapshot does not exist, do required configurations in guest OS and take a base snapshot,
* get VMware Tools info,
* get VM and guest OS info,
* get guest OS IP address and add to inventory.

2. In the "block" part, write the tasks of test case execution and verification.

3. In the "block" part, use this task "common/skip_test_case.yml" to set test case result as below:
* Blocked: Test case dependency is not meet, e.g. no VMware Tools installed, no vCenter server configured for GOS customization testing.
* Not Supported: Tested function is not supported by VM on such ESXi versions or guest OS versions.
* Not Applicable: Tested function is not applicable for VM configration. e.g. enable secureboot on BIOS VM.
* Skipped: Test case will not run due to configured parameters. e.g test case 'deploy_vm' will be 'Skipped' when 'new_vm' parameter is set to false.

#### Test case "rescue"
- In the "rescure" part, the included task "common/test_rescue.yml" will fulfill below functions:
* take a failure status snapshot,
* take a failure status VM console screenshot,
* collect VM vmware.log file to current test case log folder,
* exit the whole testing if parameter "exit_testing_when_fail" is set to "True".
