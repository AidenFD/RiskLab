@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run Setup_Windows.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
if errorlevel 1 goto failed
set QT_QPA_PLATFORM=offscreen
".venv\Scripts\python.exe" -m pytest
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean RiskLab.spec
if errorlevel 1 goto failed
".venv\Scripts\python.exe" scripts\verify_release.py --executable dist\RiskLab\RiskLab.exe --output docs\windows_packaging_smoke
if errorlevel 1 goto failed
set QT_QPA_PLATFORM=
echo Verified offscreen packaged workflow. Output: dist\RiskLab\RiskLab.exe
echo Also launch normally to check native display and high-DPI behavior.
pause
exit /b 0
:failed
echo Build or verification failed. Read the error above.
pause
exit /b 1
