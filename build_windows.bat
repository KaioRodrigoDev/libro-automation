@echo off
setlocal

if not exist venv (
    py -m venv venv
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --onefile --name calibrador calibrador.py

echo.
echo Executavel gerado em: dist\calibrador.exe
