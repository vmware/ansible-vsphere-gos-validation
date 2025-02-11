// This is a Jsonnet file referring to
// https://github.com/agama-project/agama/blob/master/rust/agama-lib/share/examples/profile.jsonnet.
// Please, check https://jsonnet.org/ for more information about the language.
// For the schema, see
// https://github.com/openSUSE/agama/blob/master/rust/agama-lib/share/profile.schema.json

// The "hw.libsonnet" file contains hardware information from the "lshw" tool.
// Agama generates this file at runtime by running (with root privileges):
//
//   lshw -json
//
// There are included also helpers to search this hardware tree. To see helpers check
// "/usr/share/agama-cli/agama.libsonnet"
local agama = import 'hw.libsonnet';

// Find the biggest disk which is suitable for installing the system.
local findBiggestDisk(disks) =
  local sizedDisks = std.filter(function(d) std.objectHas(d, 'size'), disks);
  local sorted = std.sort(sizedDisks, function(x) -x.size);
  sorted[0].logicalname;

// Find the network interface name
local nicName = agama.findByID(agama.lshw, 'network').logicalname;

{
  product: {
    id: "Leap_16.0"
  },
  software: {
    patterns: [
      'gnome'
    ]
  },
{% if new_user is defined and new_user %}
  user: {
    fullName: "{{ new_user }}",
    password: "{{ vm_password }}",
    userName: "{{ new_user }}",
    autologin: true
  },
{% endif %}
  root: {
    password: "{{ vm_password }}",
    sshPublicKey: "{{ ssh_public_key }}"
  },
  localization: {
    language: "en_US",
    keyboard: "us",
    timezone: "America/New_York"
  },
  storage: {
    boot: {
      configure: true
    },
    drives: [
      {
        search: findBiggestDisk(agama.selectByClass(agama.lshw, 'disk')),
        partitions: [
          { 
           generate: "default"
          }
       ]
     },
    ]
  },
  network: {
    connections: [
      {
        id: nicName,
        interface: nicName,
        method4: "auto",
        method6: "auto",
        ignoreAutoDns: false,
        status: "up",
        autoconnect: true
      }
    ]
  },
  scripts: {
    pre: [
      {
        name: "pre_install_script",
        content: |||
          #!/bin/bash
          echo "Execute pre-install script" >/dev/ttyS0
          echo "{{ autoinstall_start_msg }}" >/dev/ttyS0

          echo "Installer environment variables:" >/dev/ttyS0
          env | sort >/dev/ttyS0

          echo "Installer filesystems:" >/dev/ttyS0
          mount >/dev/ttyS0

          ip_addr=$(ip -br -f inet addr show | grep -v 127.0.0.1 | awk '{print $3}')
          echo "{{ autoinstall_ipv4_msg }}$ip_addr" >/dev/ttyS0

          echo "Boot command:" >/dev/ttyS0
          cat /proc/cmdline >/dev/ttyS0
        |||
      }
    ],
     post: [
      {
        name: 'post_install_script',
        content: |||
          #!/bin/bash
          echo "Execute post-install script" >/dev/ttyS0
          echo "{{ autoinstall_complete_msg }}" >/dev/ttyS0
        |||
      }
    ],
    init: [
      {
        name: "init_script",
        content: |||
          #!/bin/bash
          echo "Archive Agama installation logs" >/dev/ttyS0
          cd /var/log
          tar -czvf agama-installation.tar.gz agama-installation >/dev/ttyS0
          echo "Agama installation logs can be found in /var/log/agama-installation.tar.gz" >/dev/ttyS0
        |||
      }
    ]
  }
}
