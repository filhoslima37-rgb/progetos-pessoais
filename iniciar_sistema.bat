@echo off
setlocal
cd /d "%~dp0"

py -m streamlit run app.py

if errorlevel 1 (
    echo.
    echo Nao foi possivel iniciar. Verifique o Python e instale requirements.txt.
    pause
)

endlocal
