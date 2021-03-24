# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
    name: ansible_vsphere_gosv_log
    type: notification
    short_description: Write Ansible output and test results to log files
    description:
      - This callback writes detail running log and test results to log file.
'''

import os
import time
import json
import sys
import yaml
import re
import importlib
import shutil
import logging
from datetime import datetime
from collections import OrderedDict

from ansible import context
from ansible import constants as C
from ansible.playbook.task_include import TaskInclude
from ansible.plugins.callback import CallbackBase
from ansible.module_utils._text import to_bytes, to_native, to_text

if sys.version_info.major == 2:
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    importlib.reload(sys)

class CallbackModule(CallbackBase):
    CALLBACK_NAME = 'ansible_vsphere_gosv_log'
    CALLBACK_TYPE = 'notification'
    CALLBACK_VERSION = 2.0
    CALLBACK_NEEDS_WHITELIST = False

    def __init__(self):
        super(CallbackModule, self).__init__()
        self.hosts = []
        self.play = None
        self.log_msg = ''
        self.testcases = OrderedDict()

        # Testbed Info
        self.vcenter_info = {'hostname':'',
                             'version':'',
                             'build':''}
        self.esxi_info = {'hostname':'',
                          'version':'',
                          'update_version':'',
                          'build':''}
        self.vm_info = {'VM Name': '',
                        'VM IP':'',
                        'Guest OS Type':'',
                        'VM Tools':'',
                        'Cloud-Init':'',
                        'Guest ID': '',
                        'Hardware Version':''}

        self.started_at = None
        self.finished_at = None

        self.testing_vars_file = None
        self.testing_vars = {}

        self.plugin_dir = os.path.dirname(os.path.realpath(__file__))
        self.cwd = os.path.dirname(self.plugin_dir)
        self.log_dir = os.path.join(self.cwd, "logs", time.strftime("%Y-%m-%d-%H-%M-%S"))
        self.current_log_dir = os.path.join(self.cwd, "logs/current")
        self.testrun_log_dir = None
        self.full_debug_log = "full_debug.log"
        self.failed_tasks_log = "failed_tasks.log"
        self.test_results_log = "results.log"

        # Plays and Tasks
        self._play_name = None
        self._play_path = None
        self._last_test_name = None
        self._failed_tasks_cache = {}

        self._last_task_uuid = None
        self._last_task_name = None
        self._task_type_cache = {}

        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        if os.path.exists(self.current_log_dir):
            try:
                if os.path.islink(self.current_log_dir):
                    os.unlink(self.current_log_dir)
                else:
                    shutil.rmtree(self.current_log_dir)
            except OSError as e:
                self._display.display("Error: {} : {}".format(self.current_log_dir, e.strerror), color=C.COLOR_ERROR)

        os.symlink(self.log_dir, self.current_log_dir, target_is_directory=True)

        # Set logger
        self.logger_name = "ansible-vsphere-gos-validation"
        self.logger = logging.getLogger(self.logger_name)
        self.logger.setLevel(logging.DEBUG)

        msg = self._banner("PLUGIN [{}]".format(os.path.realpath(__file__)))
        msg += "Plugin directory: {}\nProject directory: {}\nCurrent log directory: {}".format(
            self.plugin_dir, self.cwd, self.current_log_dir)
        self._display.display(msg, color=C.COLOR_VERBOSE)

    def add_logger_file_handler(self, log_file=None):
        """
        Add a file handler to logger with debug level
        """
        if not log_file:
            return

        log_file_path = os.path.join(self.log_dir, log_file)

        for lh in self.logger.handlers:
            if isinstance(lh, logging.FileHandler) and \
                os.path.realpath(log_file_path) == lh.baseFilename:
                return

        log_handler = logging.FileHandler(log_file_path)
        log_handler.setLevel(logging.DEBUG)

        # Set formatter and add it to file and console handlers
        log_format = "%(message)s"
        formatter = logging.Formatter(log_format)
        log_handler.setFormatter(formatter)

        # Add handlers to the logger
        self.logger.addHandler(log_handler)

    def remove_logger_file_handler(self, log_file=None):
        """
        Remove a file handler from logger
        """
        if not log_file:
            return

        log_file_path = os.path.join(self.log_dir, log_file)

        for lh in self.logger.handlers:
            if isinstance(lh, logging.FileHandler) and \
                os.path.realpath(log_file_path) == lh.baseFilename:
                lh.flush()
                lh.close()
                self.logger.removeHandler(lh)
                return

    def _task_start(self, task, prefix=None):
        # Cache output prefix for task if provided
        # This is needed to properly display 'RUNNING HANDLER' and similar
        # when hiding skipped/ok task results
        if prefix is not None:
            self._task_type_cache[task._uuid] = prefix

        # Preserve task name, as all vars may not be available for templating
        # when we need it later
        if self.play and self.play.strategy in ('free', 'host_pinned'):
            # Explicitly set to None for strategy free/host_pinned to account for any cached
            # task title from a previous non-free play
            self._last_task_name = None
        else:
            self._last_task_name = task.get_name().strip()

    def _banner(self, msg):
         if msg.startswith("Included"):
             return "\n{} | {:<}".format(time.strftime("%Y-%m-%d %H:%M:%S,%03d"),
                                         (msg + " ").ljust(60, '*'))
         else:
             return "\n{} | {:<}\n".format(time.strftime("%Y-%m-%d %H:%M:%S,%03d"),
                                           (msg + " ").ljust(60, '*'))

    def _print_task_details(self, result,
                           task_status=None,
                           delegated_vars=None,
                           loop_item=None,
                           ignore_errors=False):
        task = result._task
        prefix = self._task_type_cache.get(task._uuid, 'TASK')

        # Use cached task name
        task_name = self._last_task_name
        if task_name is None:
            task_name = task.get_name().strip()

        msg = ""

        # Set task banner
        task_banner = self._banner("{} [{}]".format(prefix, task_name))
        task_path = task.get_path()
        if task_path:
            task_banner += "task path: {}\n".format(task_path)

        # Print task banner if the task is changed
        if self._last_task_uuid != task._uuid:
            msg += task_banner

            # Update last task uuid
            self._last_task_uuid = result._task._uuid

        # Log exception traceback
        if task_status == "failed":
           e_traceback = self._get_exception_traceback(result._result)
           if e_traceback:
               msg += str(e_traceback)
               msg += "\n"

        if delegated_vars:
            result_host = "[{} -> {}]".format(result._host.get_name(), delegated_vars['ansible_host'])
        else:
            result_host = "[{}]".format(result._host.get_name())

        log_failed_tasks = False
        # Log task result facts
        if task_status == "ok":
            msg += "ok: {}".format(result_host)
        elif task_status == "changed":
            msg += "changed: {}".format(result_host)
        elif task_status == "failed":
            if result._task.loop:
                msg += "failed: {}".format(result_host)
            else:
                msg += "fatal: {}: FAILED!".format(result_host)
            log_failed_tasks = True
        elif task_status == "unreachable":
            msg += "fatal: {}: UNREACHABLE!".format(result_host)
            log_failed_tasks = True
        elif task_status == "skipped":
            msg += "skipping: {}".format(result_host)
        else:
            msg += result_host

        if result._task.loop:
            msg += " => (item={})".format(loop_item)

        msg += " => {}".format(self._dump_results(result._result, indent=4))

        if ignore_errors:
            msg += "\n...ignoring"
            log_failed_tasks = False

        # Add logger handler for failed tasks
        if log_failed_tasks:
            # Get the failed test case name or play name
            failed_play = self._play_path
            if self._last_test_name:
                failed_play = self._last_test_name
            elif self._play_name:
                failed_play = self._play_name

            failed_at = ""
            if failed_play not in self._failed_tasks_cache:
                self._failed_tasks_cache[failed_play] = []
                failed_at = self._banner("Failed at Play [{}]".format(failed_play))

            # If it is a failed item and not the first item, log its task name and path
            # in self.failed_tasks_log as well
            if task_path and task_path not in self._failed_tasks_cache[failed_play]:
                self._failed_tasks_cache[failed_play].append(task_path)
                if task_path not in msg:
                    failed_at += task_banner

            if failed_at:
                self.write_to_logfile(self.failed_tasks_log, failed_at)

            self.add_logger_file_handler(self.failed_tasks_log)

        self.logger.info(msg)

        # Remove logger handler for failed tasks
        if log_failed_tasks:
            self.remove_logger_file_handler(self.failed_tasks_log)

    def _get_testing_vars(self):
        if not os.path.exists(self.testing_vars_file):
            self.logger.error("Failed to get testing vars because {} doesn't exist".format(self.testing_vars_file))

        with open(self.testing_vars_file, 'r') as fd:
            self.testing_vars = yaml.load(fd, Loader=yaml.Loader)

    def _get_play_path(self, play):
        path = ""
        if hasattr(play, "_ds") and hasattr(play._ds, "_data_source"):
            path = play._ds._data_source
        return path

    def write_to_logfile(self, log_file, msg):
        log_file_path = os.path.join(self.log_dir, log_file)
        msg = msg.encode('utf-8')
        with open(log_file_path, 'ab') as fd:
            fd.write(msg)
            fd.close()

    def _print_testbed_info(self):
        """
        Print testbed information as below:

        Testbed information:
        +---------------------------------------------------------+
        | Product | Version | Build    | Hostname or IP           |
        +---------------------------------------------------------+
        | vCenter | 7.0.2   | 17694817 | 192.168.10.10            |
        +---------------------------------------------------------+
        | ESXi    | 7.0.2   | 17630552 | 192.168.10.11            |
        +---------------------------------------------------------+
        """

        if not self.vcenter_info['hostname'] and \
           'vcenter_hostname' in self.testing_vars and \
           self.testing_vars['vcenter_hostname']:
            self.vcenter_info['hostname'] = self.testing_vars['vcenter_hostname']
        if not self.esxi_info['hostname'] and \
           'esxi_hostname' in self.testing_vars and \
           self.testing_vars['esxi_hostname']:
            self.esxi_info['hostname'] = self.testing_vars['esxi_hostname']

        msg = "Testbed information:\n"
        if not self.vcenter_info['hostname'] and not self.esxi_info['hostname']:
            msg += "Not found vCenter or ESXi server information\n"
            self.logger.debug(msg)
            self._display.display(msg, color=C.COLOR_VERBOSE)
            return

        # Get version column width
        if self.esxi_info['update_version'] and \
           self.esxi_info['update_version'] != 'N/A' and \
           int(self.esxi_info['update_version']) > 0:
            self.esxi_info['version'] += " Update {}".format(self.esxi_info['update_version'])
        version_col_width = max([len('Version'), len(self.vcenter_info['version']), len(self.esxi_info['version'])])
        # Get build column width
        build_col_width = max([len('Build'), len(self.vcenter_info['build']), len(self.esxi_info['build'])])
        # Get hostname or IP column width
        hostname_col_width = max([len('Hostname or IP'), len(self.vcenter_info['hostname']), len(self.esxi_info['hostname'])])

        # Table width
        table_width = sum([9, version_col_width, build_col_width, hostname_col_width]) + 11

        row_border = "+{}+\n".format("".ljust(table_width - 2, "-"))
        row_format = "| {:<7} | {:<} | {:<} | {:<} |\n"

        # Table head
        msg += row_border
        msg += row_format.format("Product",
                                 "Version".ljust(version_col_width),
                                 "Build".ljust(build_col_width),
                                 "Hostname or IP".ljust(hostname_col_width))
        msg += row_border

        # vCenter row
        if self.vcenter_info['hostname']:
            msg += row_format.format("vCenter",
                                     self.vcenter_info['version'].ljust(version_col_width),
                                     self.vcenter_info['build'].ljust(build_col_width),
                                     self.vcenter_info['hostname'].ljust(hostname_col_width))
            msg += row_border

        # Server row
        if self.esxi_info['hostname']:
            msg += row_format.format("ESXi",
                                     self.esxi_info['version'].ljust(version_col_width),
                                     self.esxi_info['build'].ljust(build_col_width),
                                     self.esxi_info['hostname'].ljust(hostname_col_width))
            msg += row_border

        msg += "\n"
        self.logger.info(msg)
        self._display.display(msg, color=C.COLOR_VERBOSE)

    def _print_vm_info(self):
        """
        Print VM information as below:

        VM information:
        +--------------------------------------------------------+
        | VM Name             | photon-os-4.0-ansible-test       |
        +--------------------------------------------------------+
        | VM IP               | 192.168.10.125                   |
        +--------------------------------------------------------+
        | Guest OS Type       | VMware Photon OS 4.0 x86_64      |
        +--------------------------------------------------------+
        | VM Tools            | 11.2.5.26209 (build-17337674)    |
        +--------------------------------------------------------+
        | Cloud-Init          | 20.4.1                           |
        +--------------------------------------------------------+
        | Guest ID            | vmwarePhoton64Guest              |
        +--------------------------------------------------------+
        | Hardware Version    | vmx-19                           |
        +--------------------------------------------------------+
        """

        # Get VM name from testing vars file and set log dir
        msg = 'VM information:\n'

        if 'vm_name' in self.testing_vars and self.testing_vars['vm_name']:
            self.vm_info['VM Name'] = self.testing_vars['vm_name']
        else:
            msg += "Not found VM information\n"
            self.logger.debug(msg)
            self._display.display(msg, color=C.COLOR_VERBOSE)
            return

        # Get column width
        head_col_width = len("VM Hardware Version")
        vm_col_width = max([len(self.vm_info[vm_info_key])
                            for vm_info_key in self.vm_info.keys()])

        # Table width
        table_width = head_col_width + vm_col_width + 5

        row_border = '+{}+\n'.format(''.ljust(table_width, '-'))
        row_format = '| {:<} | {:<} |\n'

        # Table content
        msg += row_border
        for key in self.vm_info.keys():
            if self.vm_info[key]:
                msg += row_format.format(key.ljust(head_col_width),
                                         self.vm_info[key].ljust(vm_col_width ))
                msg += row_border

        msg += "\n"

        self.logger.info(msg)
        self._display.display(msg, color=C.COLOR_VERBOSE)

    def _print_test_results(self):
        """
        Print test results in a table as below

        Test Results (Total: 3, Failed: 1, No Run: 1, Elapsed Time: 00:18:42):
        +---------------------------------------------+
        | Name                 |   Status | Exec Time |
        +---------------------------------------------+
        | deploy_vm            | * No Run | 00:00:01  |
        +---------------------------------------------+
        | vgauth_check_service |   Passed | 00:03:02  |
        +---------------------------------------------+
        | gosc_cloudinit_dhcp  | * Failed | 00:12:58  |
        +---------------------------------------------+
        """

        total_exec_time = ""
        total_count = len(self.testcases)
        failed_count = 0
        skipped_count = 0


        if self.started_at and self.finished_at:
            total_exec_time = int(self.finished_at - self.started_at)

        # No test run
        if total_count == 0:
            msg = "Test Results (Total: 0, Elapsed Time: {}):\n".format(time.strftime("%H:%M:%S", time.gmtime(total_exec_time)))
            self.logger.info(msg)
            self._display.display(msg, color=C.COLOR_VERBOSE)
            return

        # Get the column width
        name_col_width = max([len(testname) for testname in self.testcases.keys()])
        status_col_width = max([(len(test['status']) + 2)
                                if test['status'].lower() != "passed"
                                else len(test['status'])
                                for test in self.testcases.values()])

        row_border = "+{}+\n".format("".ljust(name_col_width + status_col_width + 17, "-"))
        row_format = "| {:<} | {:<} | {:<9} |\n"

        # Table head
        msg = row_border
        msg += row_format.format("Name".ljust(name_col_width), "Status".rjust(status_col_width), "Exec Time")
        msg += row_border

        # Table rows
        for testname in self.testcases:
            test_exec_time = time.strftime('%H:%M:%S', time.gmtime(self.testcases[testname]['duration']))
            test_status = self.testcases[testname]['status']
            if test_status.lower() == 'passed':
                msg += row_format.format(testname.ljust(name_col_width), test_status.rjust(status_col_width), test_exec_time)
            else:
                msg += row_format.format(testname.ljust(name_col_width), ("* " + test_status).rjust(status_col_width), test_exec_time)
                if test_status.lower() == 'failed':
                    failed_count += 1
                else:
                    skipped_count += 1

        msg += row_border

        # Test summary
        test_summary = "Test Results (Total: {}, Failed: {}, No Run: {}, Elapsed Time: {}):\n".format(total_count,
                        failed_count, skipped_count, time.strftime("%H:%M:%S", time.gmtime(total_exec_time)))

        msg = test_summary + msg
        self.logger.info(msg)
        self._display.display(msg, color=C.COLOR_VERBOSE)

    def _get_exception_traceback(self, result):
        if 'exception' in result:
            msg = "An exception occurred during task execution. "
            msg += "The full traceback is:\n" + str(result['exception'])
            del result['exception']
            return msg

    def v2_runner_on_failed(self, result, ignore_errors=False):
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        self._clean_results(result._result, result._task.action)

        if result._task.loop and 'results' in result._result:
            self._process_items(result)

            if ignore_errors:
                # Failed items have been logged in self.failed_tasks_log
                # Append ...ignoring to these failed items
                self.write_to_logfile(self.failed_tasks_log, "...ignoring\n")
            return

        self._print_task_details(result, 'failed', delegated_vars, ignore_errors=ignore_errors)

        if not ignore_errors and \
           self._last_test_name in self.testcases and \
           self.testcases[self._last_test_name]['status'] == 'Running':
            self.testcases[self._last_test_name]['status'] = 'Failed'
            self.testcases[self._last_test_name]['finished_at'] = time.time()
            self.testcases[self._last_test_name]['duration'] = int(self.testcases[self._last_test_name]['finished_at'] -
                                                                   self.testcases[self._last_test_name]['started_at'])

    def v2_runner_on_ok(self, result):
        task = result._task
        task_result = result._result
        task_args = task._attributes['args']
        task_file = os.path.basename(task.get_path()).split(':')[0].strip()
        delegated_vars = task_result.get('_ansible_delegated_vars', None)

        if isinstance(task, TaskInclude):
            return

        if result._task.loop and 'results' in result._result:
            self._process_items(result)
            return

        self._clean_results(result._result, result._task.action)
        if task_result.get('changed', False):
            self._print_task_details(result, "changed", delegated_vars)
        else:
            self._print_task_details(result, "ok", delegated_vars)

        if str(task.action) == "set_fact":
            set_fact_result = task_result.get('ansible_facts', None)
            # Update deploy_vm test case name if deploy_casename is set
            if self._last_test_name and self._last_test_name.startswith("deploy"):
                if self._last_test_name in self.testcases and set_fact_result.get("deploy_casename", None):
                    old_test_name = self._last_test_name
                    self._last_test_name = set_fact_result.get("deploy_casename")
                    self.testcases[self._last_test_name] = self.testcases[old_test_name]
                    del self.testcases[old_test_name]
            if "get_guest_system_info.yml" == task_file:
                if not self.vm_info['Guest OS Type'] and set_fact_result:
                    guest_distribution = set_fact_result.get("guest_os_ansible_distribution", None)
                    guest_disctribution_ver = set_fact_result.get("guest_os_ansible_distribution_ver", None)
                    guest_arch = set_fact_result.get("guest_os_ansible_architecture", None)
                    self.vm_info['Guest OS Type'] = "{} {} {}".format(guest_distribution, guest_disctribution_ver, guest_arch)
        elif 'print_test_result.yml' == task_file and str(task.action) == "lineinfile":
            if 'invocation' in task_result and 'module_args' in task_result['invocation']:
                test_result_line = task_result['invocation']['module_args']['line']
                if test_result_line:
                    [test_name, test_result] = test_result_line.split(':')
                    test_name = test_name.strip()
                    test_result = test_result.strip()
                    if test_name in self.testcases:
                        self.testcases[test_name]['status'] = test_result
                        self.testcases[test_name]['finished_at'] = time.time()
                        self.testcases[test_name]['duration'] = int(self.testcases[test_name]['finished_at'] -
                                                                    self.testcases[test_name]['started_at'])
        elif str(task.action) == "debug":
            if re.match("skip\\s+testcase:", task.name.lower()):
                test_name = task.name.split(':')[-1].strip()
                self.testcases[test_name]['status'] = "No Run"
                self.testcases[test_name]['finished_at'] = time.time()
                self.testcases[test_name]['duration'] = int(self.testcases[test_name]['finished_at'] -
                                                            self.testcases[test_name]['started_at'])
            elif 'var' in task_args:
                debug_var_name = str(task_args['var'])
                debug_var_value = str(task_result[debug_var_name])
                if not self.testrun_log_dir and debug_var_name == 'testrun_log_path':
                    self.testrun_log_dir = debug_var_value
                if "deploy_vm.yml" == task_file:
                    if not self.vm_info['VM IP'] and debug_var_name == "vm_guest_ip":
                        self.vm_info['VM IP'] = debug_var_value
                if "test_setup.yml" == task_file:
                    if not self.vm_info['VM IP'] and debug_var_name == "vm_guest_ip":
                        self.vm_info['VM IP'] = debug_var_value
                    if not self.vm_info['Guest ID'] and debug_var_name == "vm_guest_id":
                        self.vm_info['Guest ID'] = debug_var_value
                    if not self.vm_info['Hardware Version'] and debug_var_name == "vm_hardware_version":
                        self.vm_info['Hardware Version'] = debug_var_value
                    if not self.vm_info['VM Tools'] and debug_var_name ==  "vmtools_info_from_vmtoolsd":
                        self.vm_info['VM Tools'] = debug_var_value
                if "esxi_get_version_build.yml" == task_file:
                    if not self.esxi_info['hostname'] and debug_var_name == "esxi_hostname":
                        self.esxi_info['hostname'] = debug_var_value
                    if not self.esxi_info['version'] and debug_var_name == "esxi_version":
                        self.esxi_info['version'] = debug_var_value
                    if not self.esxi_info['build'] and debug_var_name == "esxi_build":
                        self.esxi_info['build'] = debug_var_value
                    if not self.esxi_info['update_version'] and debug_var_name == "esxi_update_version":
                        self.esxi_info['update_version'] = debug_var_value
                if "vcenter_get_version_build.yml" == task_file:
                    if not self.vcenter_info['hostname'] and debug_var_name == "vcenter_hostname":
                        self.vcenter_info['hostname'] = debug_var_value
                    if not self.vcenter_info['version'] and debug_var_name == "vcenter_version":
                        self.vcenter_info['version'] = debug_var_value
                    if not self.vcenter_info['build'] and debug_var_name == "vcenter_build":
                        self.vcenter_info['build'] = debug_var_value
                if "cloudinit_version_get.yml" == task_file:
                    if not self.vm_info['Cloud-Init'] and debug_var_name == "cloudinit_version":
                        self.vm_info['Cloud-Init'] = debug_var_value

    def v2_runner_on_skipped(self, result):
        self._clean_results(result._result, result._task.action)
        if result._task.loop and 'results' in result._result:
            self._process_items(result)
        else:
            self._print_task_details(result, "skipped")

    def v2_runner_on_unreachable(self, result):
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        self._print_task_details(result, "unreachable", delegated_vars)

        if self._last_test_name in self.testcases and \
           self.testcases[self._last_test_name]['status'] == 'Running':
            self.testcases[self._last_test_name]['status'] = 'Failed'
            self.testcases[self._last_test_name]['finished_at'] = time.time()
            self.testcases[self._last_test_name]['duration'] = int(self.testcases[self._last_test_name]['finished_at'] -
                                                                   self.testcases[self._last_test_name]['started_at'])

    def v2_runner_retry(self, result):
        task_name = result.task_name or result._task
        msg = "FAILED - RETRYING: {} ({} retries left).".format(task_name, result._result['retries'] - result._result['attempts'])
        msg += "Result was: %s" % self._dump_results(result._result, indent=4)
        self.logger.debug(msg)

    def v2_runner_item_on_ok(self, result):
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        if isinstance(result._task, TaskInclude):
            return

        self._clean_results(result._result, result._task.action)
        if result._result.get('changed', False):
            self._print_task_details(result, "changed", delegated_vars, loop_item=self._get_item_label(result._result))
        else:
            self._print_task_details(result, "ok", delegated_vars, loop_item=self._get_item_label(result._result))

    def v2_runner_item_on_failed(self, result):
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        self._clean_results(result._result, result._task.action)
        self._print_task_details(result, "failed", delegated_vars, loop_item=self._get_item_label(result._result))

    def v2_runner_item_on_skipped(self, result):
        self._clean_results(result._result, result._task.action)
        self._print_task_details(result, "skipped", loop_item=self._get_item_label(result._result))

    def v2_playbook_on_start(self, playbook):
        playbook_path = os.path.realpath(playbook._file_name)
        self.started_at = time.time()

        # Parse extra vars
        extra_vars = {}
        if context.CLIARGS and context.CLIARGS['extra_vars']:
            for extra_vars_str in context.CLIARGS['extra_vars']:
                if extra_vars_str:
                    #extra_var_str is tuple
                    extra_vars_list = extra_vars_str.split()
                    for extra_vars_item in extra_vars_list:
                        if extra_vars_item.find("=") != -1:
                            extra_vars[extra_vars_item.split("=")[0].strip()] = extra_vars_item.split("=")[1].strip()

        #Use user-defined testing vars file
        if 'testing_vars_file' in extra_vars.keys():
            self.testing_vars_file = os.path.realpath(extra_vars['testing_vars_file'])
        else:
            #Use default testing vars file
            self.testing_vars_file = os.path.join(self.cwd, "vars/test.yml")

        self._get_testing_vars()

        self.add_logger_file_handler(self.full_debug_log)
        msg = self._banner("PLAYBOOK: {}".format(playbook_path))
        msg += "Positional arguments: {}\n".format(' '.join(context.CLIARGS['args']))
        msg += "Tesing vars file: {}\n".format(self.testing_vars_file)
        msg += "Playbook dir: {}\n".format(self.cwd)
        msg += "Plugin dir: {}\n".format(self.plugin_dir)
        msg += "Log dir: {}".format(self.log_dir)
        self.logger.info(msg)

    def v2_playbook_on_play_start(self, play):
        self._play_name = play.get_name()
        self._play_path = self._get_play_path(play)

        # Update the previous test case result
        if self._last_test_name and self.testcases[self._last_test_name]['status'] == 'Running':
            self.testcases[self._last_test_name]['status'] = 'Passed'
            self.testcases[self._last_test_name]['finished_at'] = time.time()
            self.testcases[self._last_test_name]['duration'] = int(self.testcases[self._last_test_name]['finished_at'] -
                                                                   self.testcases[self._last_test_name]['started_at'])

        if self._play_name:
            msg = self._banner("PLAY [{}]".format(self._play_name))
        else:
            msg = self._banner("PLAY")

        if self._play_path:
            msg += "play path: {}".format(self._play_path)

        self.logger.info(msg)

        self.play = play

        # Clear failed tasks cache
        self._failed_tasks_cache.clear()

        testcase = {}
        # Add a test case into test case dictionary
        if self._play_name and ('linux' in self._play_path or 'windows' in self._play_path):
            testcase["status"] = "Running"
            testcase["started_at"] = time.time()
            testcase["finished_at"] = None
            testcase["duration"] = 0
            self.testcases[self._play_name] = testcase
            self._last_test_name = self._play_name

    def v2_playbook_on_stats(self, stats):
        self.finished_at = time.time()

        # Update the last testcase status
        if self._last_test_name and \
           self._last_test_name != self._play_name and \
           self._last_test_name in self.testcases and \
           self.testcases[self._last_test_name]['status'] == 'Running':
            self.testcases[self._last_test_name]['status'] = 'Passed'
            self.testcases[self._last_test_name]['finished_at'] = time.time()
            self.testcases[self._last_test_name]['duration'] = int(self.testcases[self._last_test_name]['finished_at'] -
                                                                   self.testcases[self._last_test_name]['started_at'])

        # Log play stats
        msg = self._banner("PLAY RECAP")
        hosts = sorted(stats.processed.keys())
        for h in hosts:
            t = stats.summarize(h)
            msg += "{:<30} :".format(h)
            msg += "  ok={}".format(t['ok'])
            msg += "  changed={}".format(t['changed'])
            msg += "  unreachable={}".format(t['unreachable'])
            msg += "  failed={}".format(t['failures'])
            msg += "  skipped={}".format(t['skipped'])
            msg += "  rescued={}".format(t['rescued'])
            msg += "  ignored={}".format(t['ignored'])

        self.logger.info(msg)

        # Log testcases results
        self._display.banner("TEST SUMMARY")
        self.logger.info(self._banner("TEST SUMMARY"))
        self.add_logger_file_handler(self.test_results_log)
        self._print_testbed_info()
        self._print_vm_info()
        self._print_test_results()
        self.remove_logger_file_handler(self.test_results_log)

        if self.testrun_log_dir and self.log_dir != self.testrun_log_dir:
            os.system("cp -rf {}/* {}".format(self.log_dir, self.testrun_log_dir))
            os.unlink(self.current_log_dir)
            os.system("rm -rf {}".format(self.log_dir))
            os.symlink(self.testrun_log_dir, self.current_log_dir, target_is_directory=True)

    def v2_playbook_on_task_start(self, task, is_conditional):
        self._task_start(task, prefix='TASK')

    def v2_playbook_on_include(self, included_file):
        msg = self._banner('Included: {} for {}'.format(included_file._filename, ", ".join([h.name for h in included_file._hosts])))
        label = self._get_item_label(included_file._vars)
        if label:
            msg += " => (item={})".format(label)
        self.logger.info(msg)

    def v2_playbook_on_import_for_host(self, result, imported_file):
        msg = self._banner('Imported: {} for {}'.format(imported_file._filename, ", ".join([h.name for h in imported_file._hosts])))
        label = self._get_item_label(imported_file._vars)
        if label:
            msg += " => (item={})".format(label)
        self.logger.info(msg)
