# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\Saikiran\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter\\assets\\themes\\blue.json', 'customtkinter\\assets\\themes'), ('C:\\Users\\Saikiran\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter\\assets\\themes\\dark-blue.json', 'customtkinter\\assets\\themes'), ('C:\\Users\\Saikiran\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter\\assets\\fonts\\Roboto\\Roboto-Medium.ttf', 'customtkinter\\assets\\fonts\\Roboto'), ('C:\\Users\\Saikiran\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter\\assets\\fonts\\Roboto\\Roboto-Regular.ttf', 'customtkinter\\assets\\fonts\\Roboto'), ('C:\\Users\\Saikiran\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter\\assets\\fonts\\CustomTkinter_shapes_font.otf', 'customtkinter\\assets\\fonts'), ('C:\\Users\\Saikiran\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter\\assets\\themes\\green.json', 'customtkinter\\assets\\themes'), ('C:\\Users\\Saikiran\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter\\assets\\icons\\CustomTkinter_icon_Windows.ico', 'customtkinter\\assets\\icons'), ('C:\\Users\\Saikiran\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter\\assets\\icons\\.DS_Store', 'customtkinter\\assets\\icons'), ('C:\\Users\\Saikiran\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter\\assets\\.DS_Store', 'customtkinter\\assets')],
    hiddenimports=['pystray', 'Pillow', 'customtkinter', 'pynput', 'pyperclip', 'requests'],
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
    name='ActifyXAI',
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
    icon='NONE',
)
