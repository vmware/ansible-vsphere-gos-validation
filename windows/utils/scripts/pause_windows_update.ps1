# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#
# Script to disable Windows Auto Update in registry and
# set pause Windows Update for 7 days.
#
$win_update_reg_path = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
$win_pause_update_reg_path = "HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings"
$win_update_policy_path = 'HKLM:\SOFTWARE\Microsoft\PolicyManager\current\device\Update'
$win_auto_update_path = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update'

# Set NoAutoUpdate
If(!(Test-Path -Path $win_update_reg_path))
{
    New-Item -Path $win_update_reg_path -Force
}
New-ItemProperty -Path $win_update_reg_path -Name 'NoAutoUpdate' -PropertyType DWORD -Value 1 -Force
# Never check for updates
New-ItemProperty -Path $win_auto_update_path -Name 'AUOptions' -PropertyType DWORD -Value 1 -Force

# Get current date time
$current_date_time = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')

# Get 10 days after date time
$days_after_date_time = (Get-Date).AddDays(7).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')

# Set Pause Windows update till 7 days after current date time
Set-ItemProperty -Path $win_pause_update_reg_path -Name 'PauseUpdatesStartTime' -PropertyType string -Value $current_date_time
Set-ItemProperty -Path $win_pause_update_reg_path -Name 'PauseUpdatesExpiryTime' -PropertyType string -Value $days_after_date_time
Set-ItemProperty -Path $win_pause_update_reg_path -Name 'PauseFeatureUpdatesStartTime' -PropertyType string -Value $current_date_time
Set-ItemProperty -Path $win_pause_update_reg_path -Name 'PauseFeatureUpdatesEndTime' -PropertyType string -Value $days_after_date_time
Set-ItemProperty -Path $win_pause_update_reg_path -Name 'PauseQualityUpdatesStartTime' -PropertyType string -Value $current_date_time
Set-ItemProperty -Path $win_pause_update_reg_path -Name 'PauseQualityUpdatesEndTime' -PropertyType string -Value $days_after_date_time
Set-ItemProperty -Path $win_pause_update_reg_path -Name 'ExcludeWUDriversInQualityUpdate' -PropertyType string -Value 1

# Do not include driver udpate in Windows update
If(!(Test-Path -Path $win_update_policy_path))
{
    New-Item -Path $win_update_policy_path -Force
}
New-ItemProperty -Path $win_update_policy_path -Name 'ExcludeWUDriversInQualityUpdate' -PropertyType DWORD -Value 1
New-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\PolicyManager\default\Update' -Name 'ExcludeWUDriversInQualityUpdate' -PropertyType DWORD -Value 1
New-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate' -Name 'ExcludeWUDriversInQualityUpdate' -PropertyType DWORD -Value 1
