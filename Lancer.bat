@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -m word_pdf
) else (
    python -m word_pdf
)
if errorlevel 1 (
    echo.
    echo Impossible de lancer l'application. Installez Python 3.10 ou plus recent avec Tcl/Tk.
    pause
)
