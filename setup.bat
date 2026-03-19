@echo off
echo ============================================================
echo  SeamlessM4T-TD — Setup
echo ============================================================
echo.

:: --- Locate conda ---
set CONDA_EXE=
if exist "C:\ProgramData\anaconda3\Scripts\conda.exe"     set CONDA_EXE=C:\ProgramData\anaconda3\Scripts\conda.exe
if exist "%USERPROFILE%\anaconda3\Scripts\conda.exe"      set CONDA_EXE=%USERPROFILE%\anaconda3\Scripts\conda.exe
if exist "%USERPROFILE%\Miniconda3\Scripts\conda.exe"     set CONDA_EXE=%USERPROFILE%\Miniconda3\Scripts\conda.exe
if exist "C:\ProgramData\miniconda3\Scripts\conda.exe"    set CONDA_EXE=C:\ProgramData\miniconda3\Scripts\conda.exe
if "%CONDA_EXE%"=="" ( where conda >nul 2>&1 && set CONDA_EXE=conda )
if "%CONDA_EXE%"=="" (
    echo ERROR: conda not found. Install Anaconda or Miniconda first.
    pause & exit /b 1
)
echo Found conda: %CONDA_EXE%
echo.

:: --- [1/5] Create conda environment ---
echo [1/5] Creating conda environment "seamless-td" for SeamlessM4T-TD (Python 3.11)...
"%CONDA_EXE%" create -n seamless-td python=3.11 -y
if errorlevel 1 ( echo ERROR: Failed to create conda environment. & pause & exit /b 1 )

:: Derive activate path
for %%i in ("%CONDA_EXE%") do set CONDA_SCRIPTS=%%~dpi
set ACTIVATE=%CONDA_SCRIPTS%activate.bat

:: --- [2/5] Install PyTorch with CUDA 12.4 ---
echo.
echo [2/5] Installing PyTorch (CUDA 12.4)...
call "%ACTIVATE%" seamless-td
pip install torch --force-reinstall --index-url https://download.pytorch.org/whl/cu124
if errorlevel 1 ( echo ERROR: Failed to install PyTorch. & pause & exit /b 1 )

:: --- [3/5] Install remaining dependencies ---
echo.
echo [3/5] Installing dependencies...
pip install fastapi "uvicorn[standard]" python-multipart transformers scipy soundfile numpy sentencepiece tiktoken protobuf
if errorlevel 1 ( echo ERROR: Failed to install dependencies. & pause & exit /b 1 )

:: --- [4/5] Verify CUDA ---
echo.
echo [4/5] Verifying CUDA...
python -c "import torch; assert torch.cuda.is_available(), 'CUDA not available'; print('CUDA OK:', torch.cuda.get_device_name(0))"
if errorlevel 1 ( echo WARNING: CUDA check failed. The server will run on CPU. )

:: --- [5/5] Clear model cache ---
echo.
echo [5/5] Clearing HuggingFace model cache...
if exist "%USERPROFILE%\.cache\huggingface\hub\models--facebook--seamless-m4t-v2-large" (
    rmdir /s /q "%USERPROFILE%\.cache\huggingface\hub\models--facebook--seamless-m4t-v2-large"
    echo Cleared SeamlessM4T cache.
) else (
    echo No cache to clear.
)

echo.
echo ============================================================
echo  SeamlessM4T-TD setup complete. Run start_server.bat to launch the server.
echo ============================================================
pause
