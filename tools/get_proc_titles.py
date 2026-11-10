import subprocess
import json

ps_cmd = "Get-Process | Where-Object { $_.MainWindowTitle.Length -gt 0 } | Select-Object Id, ProcessName, MainWindowTitle | ConvertTo-Json"
res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
print("Processes with Window Titles:")
print(res.stdout)
