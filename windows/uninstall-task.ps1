# uninstall-task.ps1 — removes the Claude Remote Control logon task and its
# generated cmd wrapper. Leaves the .ps1 launcher and env file in place
# (delete those manually if you want a clean wipe).

$ErrorActionPreference = 'Stop'

Unregister-ScheduledTask -TaskName 'claude-remote' -TaskPath '\Claude\' -Confirm:$false

$RunDir = Join-Path $env:LOCALAPPDATA 'claude-remote'
if (Test-Path -LiteralPath $RunDir) {
    Remove-Item -LiteralPath $RunDir -Recurse -Force
}

Write-Host "Task unregistered, runtime dir removed."
