# claude-remote.ps1 — PowerShell launcher around `claude remote-control`.
#
# Mirrors bin/claude-remote (bash). Reads the same ~/.config/claude-remote.env
# the Linux/macOS launchers do, so cross-platform users can share a config
# file via dotfiles.
#
# Compatible with Windows PowerShell 5.1 (ships with Windows 10/11) and
# PowerShell 7+. No external modules required.

$ErrorActionPreference = 'Stop'

$MinVersion = [version]'2.1.51'

$EnvFile = if ($env:CLAUDE_REMOTE_ENV_FILE) {
    $env:CLAUDE_REMOTE_ENV_FILE
} else {
    Join-Path $env:USERPROFILE '.config\claude-remote.env'
}

function Die([string]$msg) {
    [Console]::Error.WriteLine("claude-remote: $msg")
    exit 1
}

# Source env file if present. Parses simple KEY=value lines, strips
# surrounding quotes, expands $HOME (POSIX style) and %VAR% (Windows style)
# so the same example file works across OSes.
if (Test-Path -LiteralPath $EnvFile) {
    Get-Content -LiteralPath $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -eq '' -or $line.StartsWith('#')) { return }
        if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            $name = $Matches[1]
            $value = $Matches[2].Trim()
            if (($value.StartsWith('"') -and $value.EndsWith('"')) -or
                ($value.StartsWith("'") -and $value.EndsWith("'"))) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            $value = $value -replace '\$HOME', $env:USERPROFILE
            $value = [Environment]::ExpandEnvironmentVariables($value)
            Set-Item -Path "env:$name" -Value $value
        }
    }
}

if ($env:CLAUDE_REMOTE_DIR) {
    if (-not (Test-Path -LiteralPath $env:CLAUDE_REMOTE_DIR -PathType Container)) {
        Die "CLAUDE_REMOTE_DIR='$($env:CLAUDE_REMOTE_DIR)' is not a directory"
    }
    Set-Location -LiteralPath $env:CLAUDE_REMOTE_DIR
}

$ClaudeBin = if ($env:CLAUDE_BIN) { $env:CLAUDE_BIN } else { 'claude' }
if (-not (Get-Command $ClaudeBin -ErrorAction SilentlyContinue)) {
    Die "'$ClaudeBin' not found in PATH. Install Claude Code first."
}

$rawVersion = & $ClaudeBin --version 2>$null
$firstToken = ($rawVersion -split '\s+', 2)[0]
if (-not $firstToken) {
    Die "could not parse 'claude --version' output: '$rawVersion'"
}

# Strip pre-release suffix (e.g. '2.2.0-rc.1' -> '2.2.0') so [version] parses.
$cleanToken = ($firstToken -split '-', 2)[0]
try {
    $current = [version]$cleanToken
} catch {
    Die "could not parse '$firstToken' as a version"
}

if ($current -lt $MinVersion) {
    Die "Remote Control needs claude >= $MinVersion (found $firstToken)"
}

# If caller didn't pass --name, default to "<host>-<dirname>".
$hasName = $false
foreach ($a in $args) {
    if ($a -eq '--name' -or $a -like '--name=*') { $hasName = $true; break }
}

$argList = @($args)
if (-not $hasName) {
    $hostname = $env:COMPUTERNAME.ToLower()
    $dirname = Split-Path -Leaf (Get-Location).Path
    $argList = @('--name', "$hostname-$dirname") + $argList
}

& $ClaudeBin remote-control @argList
exit $LASTEXITCODE
