$ErrorActionPreference = "Stop"

if (-not (Test-Path "venv")) {
    py -m venv venv
}

& .\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install opencv-python numpy certifi selenium
pip install pyinstaller

python -m PyInstaller --clean --noconfirm --onefile --name calibrador `
    --collect-all cv2 `
    --collect-submodules cv2 `
    --collect-all numpy `
    --collect-all certifi `
    --hidden-import cv2 `
    calibrador.py

python -m PyInstaller --clean --noconfirm --onefile --name automacao `
    --collect-all cv2 `
    --collect-submodules cv2 `
    --collect-all numpy `
    --collect-all certifi `
    --collect-all selenium `
    --hidden-import cv2 `
    --hidden-import selenium `
    automacao.py

Write-Host ""
Write-Host "Executaveis gerados em: dist\calibrador.exe e dist\automacao.exe"
