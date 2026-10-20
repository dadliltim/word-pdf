@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -m word_pdf.web
) else (
    python -m word_pdf.web
)
if errorlevel 1 (
    echo Verifiez Python 3.10 ou plus recent. Si le port est occupe : py -3 -m word_pdf.web --port 8766
    pause
)
