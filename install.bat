@echo off
echo ========================================
echo    CatzLauncher Electron - Installation
echo ========================================
echo.

REM Vérifier si Node.js est installé
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: Node.js n'est pas installé.
    echo Veuillez installer Node.js depuis https://nodejs.org/
    echo.
    pause
    exit /b 1
)

echo Node.js detecte: 
node --version
echo.

REM Vérifier si npm est installé
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: npm n'est pas installé.
    echo Veuillez installer npm avec Node.js
    echo.
    pause
    exit /b 1
)

echo npm detecte:
npm --version
echo.

REM Installer les dépendances
echo Installation des dependances...
npm install

if %errorlevel% neq 0 (
    echo ERREUR: Echec de l'installation des dependances.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo    Installation terminee avec succes !
echo ========================================
echo.
echo Pour lancer CatzLauncher en mode developpement:
echo   npm run dev
echo.
echo Pour construire l'application:
echo   npm run build
echo.
echo Pour lancer l'application:
echo   npm start
echo.

pause 