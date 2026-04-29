#!/bin/zsh

set -e

PYINSTALLER_CONFIG_DIR=/private/tmp/pyinstaller \
./venv/bin/python -m PyInstaller --onefile --name calibrador calibrador.py

echo "Executavel gerado em: dist/calibrador"
