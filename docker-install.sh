#!/bin/bash

echo "🐳 Installation du moniteur d'emails avec Docker"

# Vérifier que Docker est installé
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Installation..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "✅ Docker installé. Redémarrez votre session pour utiliser Docker sans sudo."
fi

# Vérifier que Docker Compose est installé
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé. Installation..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
fi

# Créer le fichier config.json s'il n'existe pas
if [ ! -f "config.json" ]; then
    echo "📝 Création du fichier config.json..."
    cp config.json.example config.json
    echo "⚠️  IMPORTANT: Éditez config.json avec vos paramètres avant de continuer!"
    echo "   nano config.json"
    read -p "Appuyez sur Entrée une fois que vous avez configuré config.json..."
fi

# Créer le dossier logs
mkdir -p logs

# Construire et lancer le conteneur
echo "🏗️  Construction de l'image Docker..."
docker-compose build

echo "🚀 Lancement du conteneur..."
docker-compose up -d

echo ""
echo "✅ Email Monitor est maintenant en cours d'exécution !"
echo ""
echo "📊 Commandes utiles :"
echo "   docker-compose logs -f        # Voir les logs en temps réel"
echo "   docker-compose stop           # Arrêter le service"
echo "   docker-compose start          # Redémarrer le service"
echo "   docker-compose restart        # Redémarrer le service"
echo "   docker-compose down           # Arrêter et supprimer le conteneur"
echo "   docker-compose ps             # Voir le statut du conteneur"
echo ""
echo "🔍 Vérification du statut :"
docker-compose ps
echo ""
echo "📝 Logs récents :"
docker-compose logs --tail=20 