@echo off
chcp 65001 > nul
echo ========================================================
echo   Web Video Caster - Windows 11 EXE Derleyici (PyInstaller)
echo ========================================================
echo.

:: Python kontrolü
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [HATA] Python sisteminizde bulunamadi!
    echo Lutfen https://www.python.org adresinden Python 3.10+ kurun.
    pause
    exit /b 1
)

:: Sanal ortam kontrolü / oluşturulması
if not exist "venv" (
    echo [BILGI] Sanal ortam (venv) olusturuluyor...
    python -m venv venv
)

echo [BILGI] Sanal ortam aktif ediliyor...
call venv\Scripts\activate

echo [BILGI] Gereksinimler yukleniyor...
pip install -r requirements.txt

echo.
echo [BILGI] PyInstaller ile WVC_Caster.exe derleniyor...
echo Lutfen bekleyin, bu islem 1-2 dakika surebilir...
echo.

pyinstaller --noconfirm --onedir --windowed ^
    --name "WVC_Caster" ^
    --add-data "src/receiver_web;src/receiver_web" ^
    main.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo   [BASARILI] Uygulama basariyla derlendi!
    echo   Klasor: dist\WVC_Caster\WVC_Caster.exe
    echo ========================================================
    echo.
    explorer dist\WVC_Caster
) else (
    echo.
    echo [HATA] Derleme sirasinda bir sorun olustu.
)

pause
