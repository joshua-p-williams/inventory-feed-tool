param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

Push-Location $ProjectRoot
try {

    if ($Clean) {
        Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
    }

    python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    python -m pip install -e ".[packaging]"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    python -m PyInstaller --noconfirm packaging/InventoryFeedTool.spec
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "Windows build created at dist/InventoryFeedTool"
}
finally {
    Pop-Location
}
