@echo off
title Prueba ver-video
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0probar.ps1"
echo.
echo Prueba terminada. Registro en prueba_log.txt
pause
