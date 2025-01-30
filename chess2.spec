# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/gui/app.py'],
    pathex=[],
    binaries=[],
    datas=[('src/assets/*', 'assets/')],  # Make sure trailing slash is included
    hiddenimports=['pygame'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Chess2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for no console window
    icon='src/assets/icon.ico'
)

# For macOS
app = BUNDLE(
    exe,
    name='Chess2.app',
    icon='src/assets/icon.icns',
    bundle_identifier='com.chess2'
) 