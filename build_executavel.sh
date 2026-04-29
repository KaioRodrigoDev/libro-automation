#!/bin/zsh

set -e

PYINSTALLER_CONFIG_DIR=/private/tmp/pyinstaller \
./venv/bin/python -m PyInstaller --clean --noconfirm --onefile --name calibrador \
  --collect-all cv2 \
  --collect-all numpy \
  --collect-all certifi \
  --hidden-import cv2 \
  calibrador.py

echo "Executavel gerado em: dist/calibrador"
