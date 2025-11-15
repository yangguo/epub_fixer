@echo off
REM Simple batch script to check EPUB files using epubcheck
REM Usage: check_epub_simple.bat <epub_file>

if "%1"=="" (
    echo Usage: check_epub_simple.bat ^<epub_file^>
    echo Example: check_epub_simple.bat mybook.epub
    pause
    exit /b 1
)

if not exist "%1" (
    echo Error: File "%1" not found!
    pause
    exit /b 1
)

if not exist "epubcheck.jar" (
    echo Error: epubcheck.jar not found in current directory!
    pause
    exit /b 1
)

echo Checking EPUB file: %1
echo Running epubcheck...
echo.

REM Run epubcheck and redirect output to file
java -jar epubcheck.jar "%1" > output.txt 2>&1

REM Display the results
type output.txt

echo.
echo Results saved to output.txt
pause