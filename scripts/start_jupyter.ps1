# Start Jupyter with the complete repository as its working directory.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$projectPython = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Die Python-Umgebung fehlt. Fuehre zuerst scripts/setup.ps1 aus.'
}
Write-Host 'Jupyter startet. Oeffne den unten ausgegebenen http://localhost-Link im Browser.'
Write-Host 'Dieses Terminal bleibt belegt. Weitere Befehle in einem zweiten Terminal ausfuehren.'
Write-Host 'Zum Beenden: Strg+C, dann die Rueckfrage bestaetigen.'
Push-Location $projectRoot
try {
    & $projectPython -m jupyterlab --no-browser "--ServerApp.root_dir=$projectRoot" '--ServerApp.default_url=/lab/tree/notebooks/01_getting_started.ipynb'
    if ($LASTEXITCODE -ne 0) { throw 'Jupyter wurde mit einem Fehler beendet.' }
} finally {
    Pop-Location
}
