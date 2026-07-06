# Registers EventX to run every 6 hours via Windows Task Scheduler.
# Run once: powershell -ExecutionPolicy Bypass -File scripts\install-task.ps1

$TaskName = "EventX Hackathon Alerts"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RunScript = Join-Path $PSScriptRoot "run.ps1"

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$RunScript`"" `
    -WorkingDirectory $ProjectRoot

# Start in 2 minutes, repeat every 6 hours for 10 years
$StartAt = (Get-Date).AddMinutes(2)
$Trigger = New-ScheduledTaskTrigger `
    -Once `
    -At $StartAt `
    -RepetitionInterval (New-TimeSpan -Hours 6) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Description "Fetches Bangalore hackathons from Unstop and sends Telegram alerts every 6 hours." `
        -Force | Out-Null
}
catch {
    # Fallback: schtasks CLI (more reliable on some Windows versions)
    $tr = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$RunScript`""
    schtasks /Create /F /TN $TaskName /TR $tr /SC HOURLY /MO 6 /RL LIMITED | Out-Null
}

Write-Host "Scheduled task '$TaskName' created."
Write-Host "Runs every 6 hours. Logs: logs\eventx.log"
Write-Host ""
Write-Host "Useful commands:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'   # run now"
Write-Host "  Get-ScheduledTask -TaskName '$TaskName'    # check status"
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false  # remove"
