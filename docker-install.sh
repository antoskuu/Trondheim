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

# Détecter la commande docker-compose correcte
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ Docker Compose n'est pas installé. Installation..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
    DOCKER_COMPOSE="docker compose"
fi

echo "📋 Utilisation de: $DOCKER_COMPOSE"

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
$DOCKER_COMPOSE build

echo "🚀 Lancement du conteneur..."
$DOCKER_COMPOSE up -d

echo ""
echo "✅ Email Monitor est maintenant en cours d'exécution !"
echo ""
echo "📊 Commandes utiles :"
echo "   $DOCKER_COMPOSE logs -f        # Voir les logs en temps réel"
echo "   $DOCKER_COMPOSE stop           # Arrêter le service"
echo "   $DOCKER_COMPOSE start          # Redémarrer le service"
echo "   $DOCKER_COMPOSE restart        # Redémarrer le service"
echo "   $DOCKER_COMPOSE down           # Arrêter et supprimer le conteneur"
echo "   $DOCKER_COMPOSE ps             # Voir le statut du conteneur"
echo ""
echo "🔍 Vérification du statut :"
$DOCKER_COMPOSE ps
echo ""
echo "📝 Logs récents :"
$DOCKER_COMPOSE logs --tail=20 