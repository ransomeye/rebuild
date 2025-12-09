@echo off
REM Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/installer/uninstall.bat
REM Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
REM Details of functionality of this file: Uninstall script to remove RansomEye Agent service and files

@echo off
setlocal

echo Uninstalling RansomEye Windows Agent...
echo.

REM Stop and remove service
sc query RansomEyeAgent >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Stopping service...
    net stop RansomEyeAgent
    timeout /t 3 /nobreak >nul
    
    echo Removing service...
    sc delete RansomEyeAgent
    timeout /t 2 /nobreak >nul
)

REM Uninstall via MSI if available
set MSI_FILE=%~dp0RansomEyeAgent.msi
if exist "%MSI_FILE%" (
    echo Running MSI uninstaller...
    msiexec /x "%MSI_FILE%" /qn /l*v "%TEMP%\RansomEyeAgent_uninstall.log"
)

REM Cleanup directories (optional - be careful)
echo.
echo Uninstallation completed.
echo Note: Configuration and data directories in %ProgramData%\RansomEye are preserved.
echo To remove all data, manually delete: %ProgramData%\RansomEye

endlocal

