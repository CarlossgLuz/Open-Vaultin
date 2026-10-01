# Final installer gate: vaultinctl health must pass before installation is considered successful.
$ErrorActionPreference = "Stop"

function Invoke-NativeChecked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
    )
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

# Vaultin requires Python 3.11+.
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Source = Join-Path $Root "src"
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
Invoke-NativeChecked $Python -c "import sys; assert sys.version_info >= (3,11), 'Vaultin requires Python 3.11 or newer'"
$State = Join-Path $HOME ".vaultin"
$Venv = Join-Path $State "venv"
$Bin = Join-Path $State "bin"
New-Item -ItemType Directory -Force -Path $State, $Bin | Out-Null
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $State "root"), $Root, $Utf8NoBom)
Invoke-NativeChecked $Python -m venv $Venv
$Vpy = Join-Path $Venv "Scripts\python.exe"
Invoke-NativeChecked $Vpy -m pip install --upgrade pip
Invoke-NativeChecked $Vpy -m pip install --editable $Root
$env:VAULTIN_EXPECTED_SOURCE = $Source
$env:PYTHONPATH = "$Source;$env:PYTHONPATH"
Invoke-NativeChecked $Vpy -c "import os, pathlib, vaultin; loaded=pathlib.Path(vaultin.__file__).resolve(); expected=pathlib.Path(os.environ['VAULTIN_EXPECTED_SOURCE']).resolve(); assert loaded.is_relative_to(expected), f'Vaultin import source mismatch: {loaded} not under {expected}'; print(f'Vaultin runtime source: {loaded}')"

$VaultinCtl = Join-Path $Venv "Scripts\vaultinctl.exe"
$Cli = Join-Path $Bin "vaultinctl.cmd"
$Hook = Join-Path $Bin "vaultinctl-hook.cmd"
$CliBody = "@echo off`r`nset `"PYTHONPATH=$Source;%PYTHONPATH%`"`r`n`"$Vpy`" -m vaultin.cli %*`r`n"
$HookBody = "@echo off`r`nset `"PYTHONPATH=$Source;%PYTHONPATH%`"`r`n`"$Vpy`" -m vaultin.hooks.entrypoint %* --root `"$Root`"`r`n"
Set-Content -Path $Cli -Encoding ASCII -Value $CliBody
Set-Content -Path $Hook -Encoding ASCII -Value $HookBody

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$UserParts = @($UserPath -split ";" | Where-Object { $_ })
if ($UserParts -notcontains $Bin) {
    [Environment]::SetEnvironmentVariable("Path", (($UserParts + $Bin) -join ";"), "User")
}
if (($env:Path -split ";") -notcontains $Bin) {
    $env:Path = "$Bin;$env:Path"
}

$PluginRoot = Join-Path $HOME ".codex\plugins\vaultin"
$PluginCache = Join-Path $HOME ".codex\plugins\cache\vaultin-personal\vaultin"
if (Test-Path $PluginRoot) { Remove-Item -Recurse -Force $PluginRoot }
if (Test-Path $PluginCache) { Remove-Item -Recurse -Force $PluginCache }
New-Item -ItemType Directory -Force -Path (Split-Path $PluginRoot) | Out-Null
Copy-Item -Recurse -Force (Join-Path $Root "adapters\codex-plugin") $PluginRoot
Invoke-NativeChecked $Vpy -m vaultin.adapters.codex_install --home $HOME --hooks-template (Join-Path $Root "adapters\codex-plugin\hooks\hooks.json") --hook-command $Hook

$HooksPath = Join-Path $PluginRoot "hooks\hooks.json"
$HooksJson = Get-Content -Raw $HooksPath | ConvertFrom-Json
foreach ($Property in $HooksJson.hooks.PSObject.Properties) {
    foreach ($Matcher in $Property.Value) {
        foreach ($Entry in $Matcher.hooks) {
            if ($Entry.type -eq "command") {
                $Entry.command = $Entry.command -replace '^vaultinctl-hook', ('"' + $Hook + '"')
            }
        }
    }
}
$HooksJson | ConvertTo-Json -Depth 20 | Set-Content -Path $HooksPath -Encoding UTF8

Invoke-NativeChecked $Cli health --root $Root
Write-Host "Vaultin installed. CLI available as vaultinctl. Codex hook uses the absolute wrapper $Hook."
