@echo off
rem Crea dist\Clawd.exe: un solo archivo, sin ventana de consola y con el icono de Clawd.
rem Antes hace falta:  py -m pip install pyinstaller pillow
py -m PyInstaller --noconfirm --onefile --windowed --name Clawd --icon clawd.ico clawd_escritorio.py
echo.
echo Listo: dist\Clawd.exe
