@ echo off
REM this script will be executed after quiesce snapshot taking
powershell.exe (New-TimeSpan -Start (Get-Date "01/01/1970") -End (Get-Date)).TotalSeconds > C:\test_post_thaw.txt
