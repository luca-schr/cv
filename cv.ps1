# Usage:
#   .\cv.ps1 webmaster
#   .\cv.ps1 exemple-fullstack-react-nest
#   .\cv.ps1 -Master

param(
    [Parameter(Position = 0)]
    [string]$Job,

    [switch]$Master,
    [switch]$MdOnly,
    [switch]$NoLlm
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
$env:WEASYPRINT_DLL_DIRECTORIES = "C:\msys64\mingw64\bin"

$buildArgs = @("$Root\build.py")

if ($Master) {
    $buildArgs += "--master"
}
elseif ($Job) {
    $jobFile = Join-Path $Root "jobs\$Job.txt"
    if (-not (Test-Path $jobFile)) {
        Write-Error "Fichier introuvable : jobs\$Job.txt"
    }
    $buildArgs += $jobFile
}
else {
    Write-Host "Usage:"
    Write-Host "  .\cv.ps1 webmaster"
    Write-Host "  .\cv.ps1 -Master"
    Write-Host "  .\cv.ps1 webmaster -MdOnly"
    exit 1
}

if ($MdOnly) {
    $buildArgs += "--md-only"
}
if ($NoLlm) {
    $buildArgs += "--no-llm"
}

python @buildArgs
exit $LASTEXITCODE
