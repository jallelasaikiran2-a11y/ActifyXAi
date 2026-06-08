import PyInstaller.__main__
from PyInstaller.utils.hooks import collect_data_files
import os

if __name__ == '__main__':
    # Collect customtkinter theme data
    ctk_data = collect_data_files('customtkinter', include_py_files=False)
    add_data_args = []
    for src, dst in ctk_data:
        add_data_args.extend(['--add-data', f'{src};{dst}'])

    args = [
        'main.py',
        '--name=ActifyXAI',
        '--noconsole',
        '--noconfirm',
        '--onefile',
        '--hidden-import=pystray',
        '--hidden-import=Pillow',
        '--hidden-import=customtkinter',
        '--hidden-import=pynput',
        '--hidden-import=pyperclip',
        '--hidden-import=requests',
        '--icon=NONE',
    ] + add_data_args

    PyInstaller.__main__.run(args)
    print("Build complete. Check the 'dist' folder for ActifyXAI.exe.")
