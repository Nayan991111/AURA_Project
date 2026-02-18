# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# --- 1. COLLECT CUSTOMTKINTER ASSETS ---
tmp_ctk = collect_all('customtkinter')
datas = tmp_ctk[0]
binaries = tmp_ctk[1]
hiddenimports = tmp_ctk[2]

# --- 2. FORCE COLLECT GOOGLE LIBRARIES (THE FIX) ---
# This explicitly bundles the entire googleapiclient folder
tmp_google = collect_all('googleapiclient')
datas += tmp_google[0]
binaries += tmp_google[1]
hiddenimports += tmp_google[2]

tmp_auth = collect_all('google_auth_oauthlib')
datas += tmp_auth[0]
binaries += tmp_auth[1]
hiddenimports += tmp_auth[2]

# --- 3. COLLECT PROJECT ASSETS ---
datas += [
    ('assets', 'assets'),
    ('src', 'src'),
    # TESSERACT V5.5.2 PATH (Verified)
    ('/opt/homebrew/Cellar/tesseract/5.5.2/share/tessdata', 'tessdata'),
]

# --- 4. HIDDEN IMPORTS (Safety Net) ---
hiddenimports += [
    'google.auth.transport.requests',
    'doctr',
    'PIL',
    'pystray',
    'src.ui.app', 
    'src.services.audit_manager'
]

a = Analysis(
    ['src/utils/main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AURA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, 
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch='arm64',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AURA',
)

app = BUNDLE(
    coll,
    name='AURA.app',
    icon=None,
    bundle_identifier='org.inamigos.aura',
)