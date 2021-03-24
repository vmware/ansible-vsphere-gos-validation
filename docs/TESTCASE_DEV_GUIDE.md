# Test case development guide

## Test case:
- Create new test case folder in this path "linux/", with the name of test case, e.g., "linux/test_case_1/".
- Define test case required user configuration parameters in file "vars/test.yml", also add the description of how to use it.
- Add test case playbook to this test case list file "linux/gosv_testcase_list.yml" when the new added test case is ready.
- Use the common tasks of VM related operations in "common/" folder, tasks of guest OS related operations in "linux/utils/" folder.
- Add new common task to "common/" or "linux/utils/" if existing tasks not provide the required functionality.
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
- Playbook 'tasks' part is a "block" - "rescue" section, write all the tasks of test case execution and validation in "block" part, "rescue" part includes a common task "utils/test_rescue.yml". It means any task fails in "block" part, the testing will jump to the "rescue" part to execute failure/error handling tasks.

Below is an example of test case playbook:
```
- name: test_case_1
  hosts: localhost
  vars_files:
    - "{{ testing_vars_file | default('../../vars/test.yml') }}"
  tasks:
    - name: All the tasks of test case execution
      block:
        - include_tasks: ../utils/test_setup.yml

        # e.g., set test result to 'No Run' when VMware tools is not installed
        - include_tasks: ../../common/print_test_result.yml
          vars:
            test_result: "No Run"
          when: not vmtools_is_installed

        # e.g., run test case when VMware tools is installed
        - block: 
            - include_tasks: test_case_1_task.yml
            
            - name: Verify task result
              assert:
                that:
                  - task_result == expected_value
                fail_msg: "test_result must be expected_value"
                success_msg: "test_result is expected_value"

            # set test result to 'Passed' when check point verified
            - include_tasks: ../../common/print_test_result.yml
              vars:
                test_result: "Passed"

          when: vmtools_is_installed
      rescue:
        - include_tasks: ../utils/test_rescue.yml
```

#### Test case "block"
1. In the "block" part, the first included task is "linux/utils/test_setup.yml", this task file is executed at the beginning of each test case. It will fulfill below functions mainly:
* check base snapshot existence status, revert to it if exists or take base snapshot if does not exist,
* get VMware Tools status,
* get VM and guest OS info,
* get guest IP address and add to inventory.

2. In the "block" part, write the tasks of test case execution and verification.

3. In the "block" part, use this task "common/print_test_result.yml" to set test case result as below:
* "No Run": test case requirements or dependency not meet, 
* "Failed": test case verification failed,
* "Passed": test case passed.

#### Test case "rescue"
- In the "rescure" part, the included task "linux/utils/test_rescue.yml" will fulfill below functions:
* print "Failed" test case result,
* take a failure status snapshot by default,
* revert to base snapshot by default,
* clean up the created vSwitch, portgroup and router VM,
* exit the whole testing if parameter "exit_testing_when_fail" is set to "True".
