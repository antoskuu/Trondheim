#!/bin/bash

echo "=== Installation du moniteur d'emails Zimbra ==="

# Vérifier que Python 3 est installé
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé. Veuillez l'installer avant de continuer."
    exit 1
fi

# Créer l'environnement virtuel s'il n'existe pas
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activer l'environnement virtuel
echo "🔧 Activation de l'environnement virtuel..."
source venv/bin/activate

# Installer les dépendances
echo "📥 Installation des dépendances..."
pip install -r requirements.txt

# Vérifier que notify-send est disponible (pour les notifications desktop)
if ! command -v notify-send &> /dev/null; then
    echo "⚠️  notify-send n'est pas installé. Installation recommandée pour les notifications desktop:"
    echo "   sudo pacman -S libnotify  # Sur Arch Linux"
    echo "   sudo apt install libnotify-bin  # Sur Ubuntu/Debian"
fi

echo ""
echo "✅ Installation terminée!"
echo ""
echo "🚀 Pour démarrer le programme:"
echo "   1. Modifiez le fichier config.json avec vos paramètres"
echo "   2. Lancez: python3 mail.py"
echo ""
echo "🛑 Pour arrêter le programme: Ctrl+C"
echo ""

# Demander si l'utilisateur veut lancer maintenant
read -p "Voulez-vous lancer le programme maintenant? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🏁 Lancement du moniteur d'emails..."
    python3 mail.py
fi 