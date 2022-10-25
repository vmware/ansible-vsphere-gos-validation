# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#
# Script to deploy EFLOW VM inside the Windows
# VM on vSphere.
#
Set-ExecutionPolicy -ExecutionPolicy AllSigned -Force
$msiPath = $([io.Path]::Combine($env:TEMP, 'AzureIoTEdge.msi'))
$ProgressPreference = 'SilentlyContinue'
Invoke-WebRequest "https://aka.ms/AzEflowMSI" -OutFile $msiPath
Start-Process -Wait msiexec -ArgumentList "/i","$([io.Path]::Combine($env:TEMP, 'AzureIoTEdge.msi'))","/qn"
Deploy-Eflow -acceptEula Yes -acceptOptionalTelemetry Yes
