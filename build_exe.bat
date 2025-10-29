@echo off
REM Build MaCompta executable
pyinstaller --onefile --windowed --name MaCompta ^
  --icon assets/app.ico ^
  --add-data "assets;assets" ^
  main.py
