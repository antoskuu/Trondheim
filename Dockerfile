FROM python:3.11-slim

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root pour la sécurité
RUN useradd -m -u 1000 emailmonitor

# Définir le répertoire de travail
WORKDIR /app

# Copier les requirements en premier pour optimiser le cache Docker
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY mail.py .

# Changer le propriétaire des fichiers
RUN chown -R emailmonitor:emailmonitor /app

# Passer à l'utilisateur non-root
USER emailmonitor

# Le fichier config.json sera monté comme volume
# Commande par défaut
CMD ["python", "mail.py"] 