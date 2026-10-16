# Compile the supplied TUM report project with the local MiKTeX installation.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$gitPerlDirectory = 'C:\Program Files\Git\usr\bin'
$previousPath = $env:PATH
if (Test-Path -LiteralPath (Join-Path $gitPerlDirectory 'perl.exe')) {
    $env:PATH = $gitPerlDirectory + ';' + $env:PATH
}
Push-Location (Join-Path $projectRoot 'report')
try {
    latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
    if ($LASTEXITCODE -ne 0) { throw 'LaTeX compilation failed. See report/build/main.log.' }
} finally {
    Pop-Location
    $env:PATH = $previousPath
}
