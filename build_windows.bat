@echo off
setlocal

if not exist venv (
    py -m venv venv
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install opencv-python numpy certifi selenium
pip install pyinstaller

python -m PyInstaller --clean --noconfirm --onefile --name calibrador ^
    --collect-all cv2 ^
    --collect-submodules cv2 ^
    --collect-all numpy ^
    --collect-all certifi ^
    --hidden-import cv2 ^
    calibrador.py

python -m PyInstaller --clean --noconfirm --onefile --name automacao ^
    --collect-all cv2 ^
    --collect-submodules cv2 ^
    --collect-all numpy ^
    --collect-all certifi ^
    --collect-all selenium ^
    --hidden-import cv2 ^
    --hidden-import selenium ^
    automacao.py

echo.
echo Executaveis gerados em: dist\calibrador.exe e dist\automacao.exe
