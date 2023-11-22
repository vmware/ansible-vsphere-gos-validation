net use Z: {{ suvp_share_point }} {{ suvp_pwd }} /user:{{ suvp_name }};
Copy-Item -Path {{ msu_file_src }} -Destination {{ msu_file_dest }}  -ErrorAction Stop;
wusa.exe {{ msu_file_dest }} /quiet /norestart;
$kb_installed = Get-HotFix | Where HotFixID -eq {{ wu_kb_number }};
$check_attempt = 0;
do {
    Start-Sleep -seconds 300;
    $check_attempt = $check_attempt + 1;
    $kb_installed = Get-HotFix | Where HotFixID -eq {{ wu_kb_number }};
    Write-Host "$check_attempt Attempt";
    if ($kb_installed) {
    	Write-Host "$kb_num is installed"
        }
    }
while (!($kb_installed) -and ($check_attempt -le 11));