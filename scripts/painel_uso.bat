@echo off
rem Painel de uso privado - http://localhost:8790
rem   - se o servidor nao estiver de pe, sobe (pythonw = sem janela de console)
rem   - se ja estiver rodando, nao sobe outro
rem   - abre a pagina no navegador padrao (use --sem-abrir para so subir)
rem Usado pelo atalho do Desktop e pelo atalho da pasta Inicializar (logon).
cd /d "%~dp0.."

netstat -ano | findstr /R /C:":8790 .*LISTENING" >nul 2>&1
if errorlevel 1 (
  echo Subindo o painel de uso...
  start "" ".venv\Scripts\pythonw.exe" "scripts\27_uso.py" --servir
  ping -n 6 127.0.0.1 >nul
)

if not "%1"=="--sem-abrir" start "" "http://localhost:8790/"
