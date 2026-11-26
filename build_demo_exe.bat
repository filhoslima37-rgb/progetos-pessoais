@echo off
setlocal
cd /d "%~dp0"

py -m pip install -r requirements-build.txt
if errorlevel 1 goto erro

py -m PyInstaller --noconfirm --clean financeiro_demo.spec
if errorlevel 1 goto erro

echo.
echo Executavel criado em dist\FinanceiroDemo.exe
pause
exit /b 0

:erro
echo.
echo Falha ao preparar ou compilar o executavel. Confira Python e a conexao com a internet.
pause
exit /b 1
