@echo off
setlocal
cd /d "%~dp0"

py demo.py

if errorlevel 1 (
    echo.
    echo Nao foi possivel iniciar a demonstracao. Verifique Python e requirements.txt.
    pause
)

endlocal
