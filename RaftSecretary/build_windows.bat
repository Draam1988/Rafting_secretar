@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Installing PyInstaller...
python -m pip install --upgrade pip
python -m pip install pyinstaller

echo [2/3] Building Windows prototype...
python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onedir ^
  --windowed ^
  --name RaftSecretary ^
  --add-data "raftsecretary;raftsecretary" ^
  --add-data "data;data" ^
  launcher.py

echo [3/3] Build finished.
echo Ready folder: dist\RaftSecretary
pause
