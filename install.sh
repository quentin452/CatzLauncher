#!/bin/bash

echo "========================================"
echo "   CatzLauncher Electron - Installation"
echo "========================================"
echo

# Vérifier si Node.js est installé
if ! command -v node &> /dev/null; then
    echo "ERREUR: Node.js n'est pas installé."
    echo "Veuillez installer Node.js depuis https://nodejs.org/"
    echo
    exit 1
fi

echo "Node.js detecte:"
node --version
echo

# Vérifier si npm est installé
if ! command -v npm &> /dev/null; then
    echo "ERREUR: npm n'est pas installé."
    echo "Veuillez installer npm avec Node.js"
    echo
    exit 1
fi

echo "npm detecte:"
npm --version
echo

# Installer les dépendances
echo "Installation des dependances..."
npm install

if [ $? -ne 0 ]; then
    echo "ERREUR: Echec de l'installation des dependances."
    echo
    exit 1
fi

echo
echo "========================================"
echo "   Installation terminee avec succes !"
echo "========================================"
echo
echo "Pour lancer CatzLauncher en mode developpement:"
echo "  npm run dev"
echo
echo "Pour construire l'application:"
echo "  npm run build"
echo
echo "Pour lancer l'application:"
echo "  npm start"
echo

# Rendre le script exécutable
chmod +x install.sh 