$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$envFile = Join-Path $scriptDir ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=][^=]*?)\s*=\s*(.*)\s*$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"').Trim("'")
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

$env:PYTHONIOENCODING = "utf-8"

$python = Join-Path $scriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Error "venv not found at $python. Run: python -m venv .venv ; .\.venv\Scripts\pip install -r requirements.txt"
    exit 2
}

& $python (Join-Path $scriptDir "flight_check.py")
exit $LASTEXITCODE
