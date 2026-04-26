@echo off
REM QuizBuilder CLI launcher (Windows)
SET SCRIPT_DIR=%~dp0
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python "%SCRIPT_DIR%quizbuilder.py" %*
) else (
    where py >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        py "%SCRIPT_DIR%quizbuilder.py" %*
    ) else (
        echo Python 3 is required to run QuizBuilder. Install it from https://www.python.org/
        exit /b 1
    )
)
