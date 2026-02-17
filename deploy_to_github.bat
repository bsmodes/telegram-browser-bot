@echo off
set /p username="Enter your GitHub Username: "
set /p repo_name="Enter new Repository Name (e.g., telegram-bot): "

echo Initializing Git...
git init
git add .
git commit -m "Initial commit"

echo.
echo Creating repository on GitHub...
echo IMPORTANT: You will be asked to authenticate.
echo If you have 'gh' installed, it will use that.
echo Otherwise, it will try to add the remote directly.
echo.

rem Try using GH CLI if available
gh repo create %username%/%repo_name% --public --source=. --remote=origin
if %errorlevel% neq 0 (
    echo 'gh' CLI not found or failed. Falling back to manual remote add.
    echo.
    echo Please ensure you have created the repository '%repo_name%' on GitHub first!
    echo https://github.com/new
    echo.
    pause
    git remote add origin https://github.com/%username%/%repo_name%.git
)

echo.
echo Pushing to GitHub...
git branch -M main
git push -u origin main

echo.
echo Done! Now go to Render.com and connect this repository.
pause
