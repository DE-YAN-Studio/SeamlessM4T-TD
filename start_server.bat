@echo off
:: --- Locate conda ---
set CONDA_EXE=
if exist "C:\ProgramData\anaconda3\Scripts\conda.exe"     set CONDA_EXE=C:\ProgramData\anaconda3\Scripts\conda.exe
if exist "%USERPROFILE%\anaconda3\Scripts\conda.exe"      set CONDA_EXE=%USERPROFILE%\anaconda3\Scripts\conda.exe
if exist "%USERPROFILE%\Miniconda3\Scripts\conda.exe"     set CONDA_EXE=%USERPROFILE%\Miniconda3\Scripts\conda.exe
if exist "C:\ProgramData\miniconda3\Scripts\conda.exe"    set CONDA_EXE=C:\ProgramData\miniconda3\Scripts\conda.exe
if "%CONDA_EXE%"=="" ( where conda >nul 2>&1 && set CONDA_EXE=conda )

for %%i in ("%CONDA_EXE%") do set CONDA_SCRIPTS=%%~dpi
call "%CONDA_SCRIPTS%activate.bat" seamless-td

cd /d %~dp0
echo Starting SeamlessM4T-TD server (conda env: seamless-td) on http://127.0.0.1:8766
echo Press Ctrl+C to stop.
echo.
python -u server.py
pause
