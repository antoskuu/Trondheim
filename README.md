# Email-Monitor : Moniteur d'Emails avec Notifications Multi-Canaux

Ce projet est un script Python puissant et flexible pour surveiller une boîte mail IMAP (comme Zimbra, Gmail, etc.) et envoyer des notifications en temps réel via de multiples canaux lorsqu'un email correspondant à des filtres (mots-clés, expéditeurs) est reçu.

Idéal pour ne jamais manquer un email important, même lorsque vous n'êtes pas devant votre ordinateur.

## ✨ Fonctionnalités

- **Surveillance IMAP** : Se connecte à n'importe quel serveur email supportant IMAP/SSL.
- **Filtrage Puissant** : Déclenche des alertes basées sur les expéditeurs, les mots-clés dans le sujet ou dans le corps de l'email.
- **Notifications Multi-Canaux** :
  - 📞 **Appels Vocaux** (Twilio, CallMeBot)
  - 💬 **SMS** (Twilio)
  - 📱 **Messages WhatsApp** (Twilio, CallMeBot)
  - 🚀 **Notifications Push** (Ntfy.sh)
  - 💻 **Notifications Desktop** (Linux/Windows/macOS)
  - 🔊 **Alerte Sonore** (locale)
  - 🚨 **Alarme Intensive** : Répète une alerte sonore et visuelle plusieurs fois.
  - 🔌 **Webhook** : Intégrez le script avec n'importe quel service (Zapier, IFTTT, etc.).
- **Gestion des Dépendances** : Utilise un environnement virtuel Python pour une installation propre.
- **Déploiement Facile** : Prêt à être déployé sur un serveur (comme DigitalOcean) pour une surveillance 24/7 grâce à un service `systemd`.

## 🛠️ Installation Locale

### Prérequis
- Python 3.8+
- `pip` et `venv`

### Étapes

1.  **Clonez le dépôt :**
    ```bash
    git clone <URL_DU_REPO>
    cd Email-Monitor
    ```

2.  **Créez et activez l'environnement virtuel :**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
    *(Sur Windows, utilisez `venv\Scripts\activate`)*

3.  **Installez les dépendances :**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurez le projet :**
    -   Copiez le fichier de configuration d'exemple :
        ```bash
        cp config.json.example config.json
        ```
    -   Ouvrez `config.json` et remplissez les sections dont vous avez besoin, avec false/true (email, filtres, et les services de notification que vous voulez utiliser).

5.  **Lancez le moniteur :**
    ```bash
    python3 mail.py
    ```
    Le script commencera à surveiller votre boîte mail. Pour l'arrêter, faites `Ctrl+C`.

## ⚙️ Configuration des Services de Notification

Voici comment obtenir les clés d'API et configurer les services externes.

### 📞 Twilio (Appels & SMS)

Twilio est un service professionnel qui permet d'envoyer des SMS et de passer des appels automatisés.

1.  **Créez un compte sur [Twilio.com](https://www.twilio.com/try-twilio).**
    -   Lors de l'inscription, vous recevrez un crédit d'essai gratuit (généralement autour de 15€), ce qui est largement suffisant pour ce projet. Aucune carte de crédit n'est requise au début.

2.  **Trouvez vos identifiants :**
    -   Sur votre [console Twilio](https://console.twilio.com/), vous trouverez votre **Account SID** et votre **Auth Token**.
    -   Copiez-les dans la section `"twilio"` et `"call_twilio"` de votre `config.json`.

3.  **Obtenez un numéro de téléphone Twilio :**
    -   Allez dans la section "Phone Numbers" -> "Manage" -> "Buy a number".
    -   Choisissez un numéro gratuit avec les capacités SMS et Voix.
    -   Ce numéro sera votre `"from_number"` dans `config.json`.

### 📱 CallMeBot (Messages WhatsApp gratuits)

CallMeBot est un service gratuit qui permet d'envoyer des messages WhatsApp via une simple requête web.

1.  **Ajoutez le contact du bot :**
    -   Ajoutez ce numéro à vos contacts WhatsApp : `+34 644 19 82 24`.

2.  **Activez le service :**
    -   Envoyez ce message exact au contact du bot : `I allow callmebot to send me messages`

3.  **Recevez votre clé API :**
    -   Le bot vous répondra avec votre clé API (une chaîne de chiffres).
    -   Copiez cette clé dans la section `"whatsapp_callmebot"` de `config.json`.

### 🚀 Ntfy.sh (Notifications Push gratuites)

Ntfy.sh est un service de notifications push open-source, gratuit et sans inscription.

1.  **Choisissez un nom de "topic" :**
    -   Un "topic" est simplement une URL. Pour garder vos notifications privées, inventez un nom de topic unique et difficile à deviner.
    -   Exemple : `https://ntfy.sh/mon-alerte-email-insa-a7b3c9x`

2.  **Configurez `config.json` :**
    -   Copiez cette URL complète dans le champ `"url"` de la section `"ntfy"`.

3.  **Recevez les notifications :**
    -   **Sur mobile :** Téléchargez l'application Ntfy pour [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy) ou [iOS](https://apps.apple.com/us/app/ntfy/id1625396347).
    -   **Dans l'application :** Abonnez-vous au topic que vous venez de créer.
    -   **Sur le web :** Vous pouvez aussi voir les notifications en allant simplement sur l'URL de votre topic dans un navigateur.

## 🚀 Déploiement sur un Serveur (Ex: DigitalOcean)

Pour une surveillance 24/7, il est recommandé de déployer ce script sur un serveur.

### Prérequis
- Un serveur/droplet Ubuntu 22.04.
- Accès root/sudo.

### Étapes

1.  **Préparez le serveur :**
    -   Connectez-vous en SSH à votre serveur.
    -   Uploadez les fichiers du projet (`mail.py`, `requirements.txt`, `config.json`, `deploy_digitalocean.sh`, `email-monitor.service`).
    -   Rendez le script de déploiement exécutable et lancez-le :
        ```bash
        chmod +x deploy_digitalocean.sh
        sudo ./deploy_digitalocean.sh
        ```
    Ce script va mettre à jour le système, installer Python, créer un utilisateur dédié `emailmonitor`, et préparer l'environnement.

2.  **Uploadez vos fichiers et configurez :**
    -   Depuis votre machine locale, uploadez les fichiers du projet dans le répertoire de l'utilisateur `emailmonitor` :
        ```bash
        scp mail.py requirements.txt config.json emailmonitor@VOTRE_IP_SERVEUR:/home/emailmonitor/email-monitor/
        ```
        *(Assurez-vous que votre `config.json` est configuré pour le serveur, c'est-à-dire sans notifications desktop/sonores).*

3.  **Installez et lancez le service :**
    -   Connectez-vous à nouveau au serveur.
    -   Copiez le fichier de service `systemd` :
        ```bash
        sudo cp email-monitor.service /etc/systemd/system/
        ```
    -   Activez et démarrez le service :
        ```bash
        sudo systemctl daemon-reload
        sudo systemctl enable email-monitor.service
        sudo systemctl start email-monitor.service
        ```

4.  **Vérifiez que tout fonctionne :**
    ```bash
    # Voir le statut du service
    sudo systemctl status email-monitor.service

    # Voir les logs en direct
    sudo journalctl -u email-monitor.service -f
    ```

Le service est maintenant actif et redémarrera automatiquement si le serveur est redémarré ou si le script rencontre une erreur.

## ⚙️ Fichiers du Projet

-   `mail.py`: Le script principal du moniteur d'emails.
-   `requirements.txt`: Les dépendances Python.
-   `config.json.example`: Fichier de configuration d'exemple. **À copier vers `config.json`**.
-   `.gitignore`: Fichiers et dossiers à ignorer par Git (notamment `config.json`).
-   `deploy_digitalocean.sh`: Script pour préparer un serveur Ubuntu.
-   `email-monitor.service`: Fichier de configuration `systemd` pour faire tourner le script en tant que service.
-   `README.md`: Ce fichier. 