@echo off
REM Path and File Name : /home/ransomeye/rebuild/ransomeye_windows_agent/installer/install.bat
REM Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
REM Details of functionality of this file: Wrapper to set global ENV vars and run msiexec /i for MSI installation

@echo off
setlocal

set MSI_FILE=%~dp0RansomEyeAgent.msi
set INSTALL_DIR=%ProgramFiles%\RansomEye\Agent

echo Installing RansomEye Windows Agent...
echo.

REM Set environment variables
setx CORE_API_URL "https://localhost:8443" /M
setx AGENT_CERT_PATH "%ProgramData%\RansomEye\certs\agent.crt" /M
setx AGENT_KEY_PATH "%ProgramData%\RansomEye\certs\agent.key" /M
setx CA_CERT_PATH "%ProgramData%\RansomEye\certs\ca.crt" /M
setx AGENT_UPDATE_KEY_PATH "%ProgramData%\RansomEye\certs\update_key.pub" /M
setx BUFFER_DIR "%ProgramData%\RansomEye\buffer" /M
setx MODEL_PATH "%ProgramData%\RansomEye\models\detector_model.pkl" /M
setx AGENT_METRICS_PORT "9111" /M

echo Environment variables set.
echo.

REM Install MSI
if exist "%MSI_FILE%" (
    echo Running MSI installer...
    msiexec /i "%MSI_FILE%" /qn /l*v "%TEMP%\RansomEyeAgent_install.log"
    
    if %ERRORLEVEL% EQU 0 (
        echo Installation completed successfully.
        echo Log file: %TEMP%\RansomEyeAgent_install.log
    ) else (
        echo Installation failed with error code %ERRORLEVEL%.
        echo Check log file: %TEMP%\RansomEyeAgent_install.log
        exit /b %ERRORLEVEL%
    )
) else (
    echo MSI file not found: %MSI_FILE%
    exit /b 1
)

endlocal

