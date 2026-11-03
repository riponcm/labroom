# Register the lab's two scheduled posts with Windows Task Scheduler.
# Switch has no scheduler, so recurring work is a scheduled chat message.
#
#   Weekdays 17:03  Maya asks logbook for the daily reminder (it tags anyone without a log today)
#   Mondays  09:03  Maya asks reporter for last week's lab board and auditor for the weekly audit
#
# Run it yourself, once, from the repo root:
#   powershell -ExecutionPolicy Bypass -File tools\schedule_lab.ps1 -Channel trailnet
# Remove later with:
#   Unregister-ScheduledTask -TaskName "LabRoom *" -Confirm:$false

param(
    [string]$Channel = "trailnet"
)

$repo = Split-Path -Parent $PSScriptRoot
$python = (Get-Command python).Source
$postAs = Join-Path $repo "tools\post_as.py"

$daily = New-ScheduledTaskAction -Execute $python -WorkingDirectory $repo -Argument (
    "`"$postAs`" maya.chen `"@logbook daily reminder, please.`" --channel $Channel")
$weekly = New-ScheduledTaskAction -Execute $python -WorkingDirectory $repo -Argument (
    "`"$postAs`" maya.chen `"@reporter last week's lab board, please. @auditor the weekly audit for last week, please.`" --channel $Channel")

$dailyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 17:03
$weeklyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 09:03

Register-ScheduledTask -TaskName "LabRoom daily log reminder" -Action $daily -Trigger $dailyTrigger -Force | Out-Null
Register-ScheduledTask -TaskName "LabRoom weekly board and audit" -Action $weekly -Trigger $weeklyTrigger -Force | Out-Null

Get-ScheduledTask -TaskName "LabRoom *" | Select-Object TaskName, State
