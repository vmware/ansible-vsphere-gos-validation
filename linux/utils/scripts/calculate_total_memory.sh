# Copyright 2021-2023 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#!/bin/bash
# Calculate total memory size in guest
totalmem=0;
for mem in /sys/devices/system/memory/memory*; do
  online=$(cat ${mem}/online); 
  if [ "$online" == "1" ] ; then
    totalmem=$((totalmem+$((0x$(cat /sys/devices/system/memory/block_size_bytes)))));
  fi
done; 
echo $((totalmem/1024**2))
