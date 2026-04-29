$ErrorActionPreference = "Stop"

if (-not (Test-Path "venv")) {
    py -m venv venv
}

& .\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --clean --noconfirm --onefile --name calibrador `
    --collect-all cv2 `
    --collect-all numpy `
    --collect-all certifi `
    --hidden-import cv2 `
    calibrador.py

Write-Host ""
Write-Host "Executavel gerado em: dist\calibrador.exe"
