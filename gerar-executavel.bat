@echo off
rem Gera a pasta do TeleZapp PRO (executavel) em build-pyinstaller\programa\TeleZapp PRO
rem Log em C:\logs\gerar-executavel.log
if not exist C:\logs mkdir C:\logs
cd /d "%~dp0"
"%~dp0venv\Scripts\python.exe" ferramentas\empacotar.py --so-programa > C:\logs\gerar-executavel.log 2>&1
echo Terminou com codigo %errorlevel%. Veja C:\logs\gerar-executavel.log
