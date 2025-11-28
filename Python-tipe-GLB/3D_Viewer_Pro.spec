# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['viewer-glb-gui.py'],
    pathex=[],
    binaries=[],
    datas=[('viewer-glb.py', '.')],
    hiddenimports=['pyglet', 'pyglet.gl', 'pyglet.window', 'pyglet.graphics', 'pyglet.math', 'trimesh', 'numpy', 'customtkinter', 'PIL', 'PIL._tkinter_finder'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='3D_Viewer_Pro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
