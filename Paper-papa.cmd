@echo off
rem Usage:
rem   Double-click this file to start Study Assistant.
rem   It changes to F:\codex\Study-Assistant, starts backend and frontend,
rem   handles busy ports automatically, and opens the browser after readiness.
rem   Run Paper-papa-stop.cmd to stop the services.

cd /d "F:\codex\Study-Assistant"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "F:\codex\Study-Assistant\Paper-papa.ps1"
pause
