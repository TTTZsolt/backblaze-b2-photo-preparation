@echo off
echo Takeout - B2 feltolto: Python-csomagok telepitese...
python -m pip install --upgrade Pillow pillow-heif
echo.
echo Kesz. Az rclone-t kulon kell telepiteni es beallitani (remote neve: b2_storage).
pause
