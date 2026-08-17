@echo off
cd /d "%~dp0"
set LOGFILE=%~dp0futtatas_eredmeny.txt

echo === Futtatas ideje: %date% %time% === > "%LOGFILE%"
python takeout_b2_teljes_egyeztetes.py >> "%LOGFILE%" 2>&1
echo. >> "%LOGFILE%"
echo Kilepesi kod: %errorlevel% >> "%LOGFILE%"

echo.
echo Kesz. A teljes futasi naplo ide keult: %LOGFILE%
echo Kilepesi kod: %errorlevel%
pause
