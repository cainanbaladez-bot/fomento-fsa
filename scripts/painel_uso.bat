@echo off
rem Sobe o painel de uso privado em http://localhost:8790 e fica de pe.
rem Usa pythonw para nao abrir janela de console. Registrado na tarefa
rem RIDAB-PainelUso (no logon); tambem serve para subir na mao.
cd /d "%~dp0.."
start "" ".venv\Scripts\pythonw.exe" "scripts\27_uso.py" --servir
