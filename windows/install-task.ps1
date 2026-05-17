# install-task.ps1 — registers the Claude Remote Control logon task.
#
# Run once after copying bin/claude-remote.ps1 to
# %USERPROFILE%\.local\bin\claude-remote.ps1 . No admin rights needed; the
# task is user-scope.
#
# The task calls a tiny generated cmd.exe wrapper so stdout/stderr can be
# redirected to a log file without us hand-quoting redirection operators
# through Task Scheduler.

$ErrorActionPreference = 'Stop'

$LauncherPath = Join-Path $env:USERPROFILE '.local\bin\claude-remote.ps1'
if (-not (Test-Path -LiteralPath $LauncherPath)) {
    throw "claude-remote.ps1 not found at $LauncherPath. Copy it there first."
}

$RunDir   = Join-Path $env:LOCALAPPDATA 'claude-remote'
$LogFile  = Join-Path $RunDir 'claude-remote.log'
$Wrapper  = Join-Path $RunDir 'run.cmd'
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

@"
@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "$LauncherPath" >> "$LogFile" 2>&1
"@ | Set-Content -LiteralPath $Wrapper -Encoding ASCII

$Action = New-ScheduledTaskAction -Execute $Wrapper

$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RestartCount 10 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName 'claude-remote' `
    -TaskPath '\Claude\' `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description 'Claude Code Remote Control (per-user logon)' `
    -Force | Out-Null

Write-Host "Task registered under \Claude\claude-remote."
Write-Host "  Logs:    $LogFile"
Write-Host "  Wrapper: $Wrapper"
Write-Host ""
Write-Host "Start it now (or just log out / log in):"
Write-Host "  Start-ScheduledTask -TaskName 'claude-remote' -TaskPath '\Claude\'"
