@echo off
echo Stormwater Analysis System Launcher
echo -----------------------------------
echo.
echo NOTE: You may see an "Entry Point Not Found" error about BGLImageCoders.dll
echo       This is normal - just click "OK" and the application will continue.
echo.

:: Set path to the script (now that we're in the src folder)
set SCRIPT_DIR=%~dp0
set MAIN_SCRIPT=%SCRIPT_DIR%stormwater_analysis.py

:: Try to find ArcGIS Pro's Python executable
set PYTHON_EXE=

:: Check common installation locations
if exist "C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" (
    set PYTHON_EXE="C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"
    goto :run_script
)

if exist "C:\Users\%USERNAME%\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" (
    set PYTHON_EXE="C:\Users\%USERNAME%\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"
    goto :run_script
)

:: If we get here, Python wasn't found
echo ERROR: Could not find ArcGIS Pro Python.
echo Please ensure ArcGIS Pro is installed and try again.
goto :end

:run_script
echo Found ArcGIS Pro Python at %PYTHON_EXE%
echo Running Stormwater Analysis...

:: Run the script directly
%PYTHON_EXE% "%MAIN_SCRIPT%"

:: Check for errors
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: The application encountered an error.
    echo Please ensure ArcGIS Pro is properly installed and you're signed in.
)

:end
pause