# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/play.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/*', 'assets')],  # Include the assets directory
    hiddenimports=[],
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
    icon='assets/icon.ico'  # Make sure this path is correct
)

# For macOS
app = BUNDLE(
    exe,
    name='Chess2.app',
    icon='assets/icon.icns',  # Make sure this path is correct
    bundle_identifier='com.chess2'  # Simplified identifier
) 