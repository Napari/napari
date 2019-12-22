echo "removing old files..."

rmdir /s /q build
rmdir /s /q dist

echo "checking installations of build tools"

REM with pyinstaller 3.5 and pyside2 I get the following error
REM https://stackoverflow.com/questions/57932432/pyinstaller-win32ctypes-pywin32-pywintypes-error-2-loadlibraryexw-the-sys
pip install pyinstaller==3.4
call conda install -y freetype

echo "building app..."

SET scriptpath=%~dp0

pyinstaller --noconfirm --clean --log-level=INFO "%scriptpath%\napari.spec"
