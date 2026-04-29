@echo off
setlocal

if not exist venv (
    py -m venv venv
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --clean --noconfirm --onefile --name calibrador ^
    --collect-all cv2 ^
    --collect-all numpy ^
    --collect-all certifi ^
    --hidden-import cv2 ^
    calibrador.py

echo.
echo Executavel gerado em: dist\calibrador.exe
