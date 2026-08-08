param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

if ($Clean) {
    Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
}

python -m pip install --upgrade pip
python -m pip install -e ".[packaging]"
python -m PyInstaller --noconfirm packaging/InventoryFeedTool.spec

Write-Host "Windows build created at dist/InventoryFeedTool"
