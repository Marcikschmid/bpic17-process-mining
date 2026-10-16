# Recreate the Python and Graphviz environment from the repository.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$previousTmpDirectory = $env:TMPDIR
$setupTemporaryDirectory = Join-Path $projectRoot 'tmp/setup'
New-Item -ItemType Directory -Path $setupTemporaryDirectory -Force | Out-Null
$env:TMPDIR = $setupTemporaryDirectory
Push-Location $projectRoot
try {
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
    }
    $projectPython = Join-Path $projectRoot '.venv/Scripts/python.exe'
    & $projectPython -c 'import sys; assert sys.version_info[:2] == (3, 12), "Use Python 3.12 for this environment."'
    if ($LASTEXITCODE -ne 0) { throw 'Python version check failed.' }
    & $projectPython -m pip install --disable-pip-version-check -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    & $projectPython -m ipykernel install --prefix (Join-Path $projectRoot '.venv') --name bpic17 --display-name 'BPIC17 (.venv)'
    if ($LASTEXITCODE -ne 0) { throw 'Notebook kernel installation failed.' }
    if (-not (Test-Path -LiteralPath '.tools/graphviz/Graphviz-16.1.0-win64/bin/dot.exe')) {
        & $projectPython scripts/setup_graphviz.py
        if ($LASTEXITCODE -ne 0) { throw 'Graphviz setup failed.' }
    }
    & $projectPython scripts/check_setup.py
    if ($LASTEXITCODE -ne 0) { throw 'Environment verification failed.' }
} finally {
    Pop-Location
    $env:TMPDIR = $previousTmpDirectory
}
