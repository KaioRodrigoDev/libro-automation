#!/bin/zsh

set -e

PYINSTALLER_CONFIG_DIR=/private/tmp/pyinstaller \
./venv/bin/python -m PyInstaller --clean --noconfirm --onefile --name calibrador \
  --collect-all cv2 \
  --collect-all numpy \
  --collect-all certifi \
  --hidden-import cv2 \
  calibrador.py

PYINSTALLER_CONFIG_DIR=/private/tmp/pyinstaller \
./venv/bin/python -m PyInstaller --clean --noconfirm --onefile --name automacao \
  --collect-all cv2 \
  --collect-all numpy \
  --collect-all certifi \
  --collect-all selenium \
  --hidden-import cv2 \
  --hidden-import selenium \
  automacao.py

echo "Executaveis gerados em: dist/calibrador e dist/automacao"
