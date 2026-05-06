@echo off
rem Usage:
rem   Double-click this file to stop services started by Paper-papa.cmd.
rem   It changes to F:\codex\Study-Assistant and stops only recorded Paper-papa PIDs.

cd /d "F:\codex\Study-Assistant"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "F:\codex\Study-Assistant\Paper-papa-stop.ps1"
pause
