import PyInstaller.__main__
import sys
import os

# Configura il build
PyInstaller.__main__.run([
    'viewer.py',
    '--onefile',  # Singolo eseguibile
    '--windowed',  # No console window (rimuovi per debug)
    '--name=3DModelViewer',
    '--add-data=.:.',  # Include file corrente directory
    '--hidden-import=pyglet',
    '--hidden-import=trimesh',
    '--hidden-import=PIL',
    '--collect-all=trimesh',
    '--collect-all=pyglet',
    '--noconfirm',
    # Per Windows:
    # '--icon=icon.ico',  # Aggiungi se hai un'icona
])