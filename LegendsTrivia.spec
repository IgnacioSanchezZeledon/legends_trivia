# LegendsTrivia_onefile.spec
# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Archivos a empacar dentro del .exe (PyInstaller los extrae en _MEIPASS al ejecutar)
DATAS = [
    ('assets/fonts/*.ttf', 'assets/fonts'),
    ('assets/images/*',    'assets/images'),
    ('assets/icons/*',     'assets/icons'),
    ('assets/music/*',     'assets/music'),
    ('assets/logos/*',     'assets/logos'),
    ('assets/sfx/*',       'assets/sfx'),
    ('data/*.json',        'data'),
]

# Hidden imports que a veces no se detectan
HIDDEN = ['tkextrafont', 'customtkinter'] + collect_submodules('pygame')

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ONE-FILE: todo se empaqueta dentro del ejecutable final
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,   # <- incluidos en EXE
    a.zipfiles,   # <- incluidos en EXE
    a.datas,      # <- incluidos en EXE
    name='LegendsTrivia',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # pon True si quieres ver prints en consola
    icon='assets/icons/app_icon.ico',
)
