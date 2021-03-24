@ echo off
REM this script will be executed before quiesce snapshot taking
powershell.exe (New-TimeSpan -Start (Get-Date "01/01/1970") -End (Get-Date)).TotalSeconds > C:\test_pre_freeze.txt
