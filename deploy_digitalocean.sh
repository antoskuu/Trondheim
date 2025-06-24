#!/bin/bash

echo "🚀 Déploiement du moniteur d'emails sur DigitalOcean"

# Mise à jour du système
apt update && apt upgrade -y

# Installation des dépendances système
apt install -y python3 python3-pip python3-venv git curl

# Installation d'outils optionnels pour notifications (si nécessaire)
apt install -y alsa-utils pulseaudio-utils

# Création d'un utilisateur non-root (sécurité)
useradd -m -s /bin/bash emailmonitor
usermod -aG sudo emailmonitor

# Changement vers l'utilisateur
su - emailmonitor << 'EOF'

# Clonage ou upload des fichiers
mkdir -p ~/email-monitor
cd ~/email-monitor

# Création de l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installation des dépendances Python
pip install requests twilio

echo "✅ Environnement préparé!"
echo "📁 Uploadez maintenant vos fichiers dans ~/email-monitor/"
echo "📝 N'oubliez pas de configurer config.json"

EOF 