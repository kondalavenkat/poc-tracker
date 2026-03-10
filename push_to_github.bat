@echo off
echo ==================================================
echo   Pushing PoC Tracker to GitHub
echo ==================================================
echo.

:: Check if git is initialized
if not exist .git (
    echo [INFO] Git repository not initialized. Initializing...
    git init
    echo [INFO] Please enter your GitHub repository URL:
    set /p REPO_URL="URL: "
    git remote add origin %REPO_URL%
    git branch -M main
)

:: Add all files
echo [1/3] Adding files to staging...
git add .
if %errorlevel% neq 0 (
    echo [ERROR] Failed to add files.
    pause
    exit /b %errorlevel%
)

:: Get a commit message (or use a default one)
set /p COMMIT_MSG="[2/3] Enter commit message (or press enter for 'Auto-update'): "
if "%COMMIT_MSG%"=="" set COMMIT_MSG="Auto-update dashboard"

:: Commit changes
git commit -m "%COMMIT_MSG%"
if %errorlevel% neq 0 (
    echo [INFO] Nothing to commit or commit failed.
)

:: Push to remote
echo [3/3] Pushing to GitHub...
git push -u origin main
if %errorlevel% neq 0 (
    echo [ERROR] Failed to push to GitHub. You may need to authenticate.
    pause
    exit /b %errorlevel%
)

echo.
echo ==================================================
echo   ✅ Successfully pushed to GitHub!
echo   Your Streamlit app should update shortly.
echo ==================================================
pause
