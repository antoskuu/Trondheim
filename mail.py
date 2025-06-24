#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Programme de surveillance d'emails Zimbra avec notifications
Surveille les nouveaux emails et envoie des notifications via différents canaux
"""

import imaplib
import email
import time
import json
import logging
import threading
import subprocess
import requests
from datetime import datetime
from email.header import decode_header
from typing import List, Dict, Optional
import re

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mail_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EmailMonitor:
    def __init__(self, config_file: str = 'config.json'):
        """Initialise le moniteur d'emails"""
        self.config = self.load_config(config_file)
        self.last_email_uid = None
        self.running = False
        self.imap = None
        
    def load_config(self, config_file: str) -> Dict:
        """Charge la configuration depuis un fichier JSON"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Fichier de configuration {config_file} non trouvé")
            self.create_default_config(config_file)
            return self.load_config(config_file)
    
    def create_default_config(self, config_file: str):
        """Crée un fichier de configuration par défaut"""
        default_config = {
            "email": {
                "server": "mail.votre-domaine.com",
                "port": 993,
                "username": "votre.email@domaine.com",
                "password": "votre_mot_de_passe",
                "use_ssl": True
            },
            "filters": {
                "senders": [
                    "expediteur1@example.com",
                    "expediteur2@example.com"
                ],
                "keywords": [
                    "urgent",
                    "important",
                    "alerte"
                ],
                "subject_keywords": [
                    "URGENT",
                    "ALERTE"
                ]
            },
            "notifications": {
                "desktop": {
                    "enabled": True
                },
                "sound": {
                    "enabled": True,
                    "sound_file": "/usr/share/sounds/alsa/Front_Left.wav"
                },
                "ntfy": {
                    "enabled": False,
                    "url": "https://ntfy.sh/votre-topic-unique",
                    "priority": "urgent"
                },
                "webhook": {
                    "enabled": False,
                    "url": "https://hooks.zapier.com/hooks/catch/...",
                    "method": "POST"
                },
                "twilio": {
                    "enabled": False,
                    "account_sid": "VOTRE_ACCOUNT_SID",
                    "auth_token": "VOTRE_AUTH_TOKEN",
                    "from_number": "+1234567890",
                    "to_number": "+0987654321"
                },
                "whatsapp_callmebot": {
                    "enabled": False,
                    "phone_number": "+33612345678",
                    "api_key": "VOTRE_CLE_API_CALLMEBOT"
                },
                "whatsapp_twilio": {
                    "enabled": False,
                    "account_sid": "VOTRE_ACCOUNT_SID",
                    "auth_token": "VOTRE_AUTH_TOKEN",
                    "from_number": "whatsapp:+14155238886",
                    "to_number": "whatsapp:+33612345678"
                },
                "call_callmebot": {
                    "enabled": False,
                    "phone_number": "+33612345678",
                    "api_key": "VOTRE_CLE_API_CALLMEBOT"
                },
                "alarm_intensive": {
                    "enabled": False,
                    "repeat_count": 5,
                    "interval_seconds": 2,
                    "sound_file": "/usr/share/sounds/alsa/Front_Left.wav"
                },
                "call_twilio": {
                    "enabled": False,
                    "account_sid": "VOTRE_ACCOUNT_SID",
                    "auth_token": "VOTRE_AUTH_TOKEN",
                    "from_number": "+15551234567",
                    "to_number": "+33612345678",
                    "message": "Vous avez reçu un email urgent. Consultez votre boîte mail."
                },
                "call_freemobile": {
                    "enabled": False,
                    "user": "VOTRE_IDENTIFIANT_FREE",
                    "pass": "VOTRE_CLE_API_FREE"
                }
            },
            "monitoring": {
                "check_interval": 5,
                "mailbox": "INBOX"
            }
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Fichier de configuration créé: {config_file}")
        logger.info("Veuillez modifier ce fichier avec vos paramètres avant de relancer le programme")
    
    def connect_to_imap(self) -> bool:
        """Se connecte au serveur IMAP Zimbra avec gestion d'erreurs améliorée"""
        max_retries = 3
        retry_delay = 30  # secondes
        
        for attempt in range(max_retries):
            try:
                # Fermer une connexion existante si elle existe
                if self.imap:
                    try:
                        self.imap.close()
                        self.imap.logout()
                    except:
                        pass
                    self.imap = None
                
                logger.info(f"Tentative de connexion IMAP {attempt + 1}/{max_retries}")
                
                if self.config['email']['use_ssl']:
                    self.imap = imaplib.IMAP4_SSL(
                        self.config['email']['server'],
                        self.config['email']['port']
                    )
                else:
                    self.imap = imaplib.IMAP4(
                        self.config['email']['server'],
                        self.config['email']['port']
                    )
                
                self.imap.login(
                    self.config['email']['username'],
                    self.config['email']['password']
                )
                
                self.imap.select(self.config['monitoring']['mailbox'])
                logger.info("Connexion IMAP établie avec succès")
                return True
                
            except Exception as e:
                error_msg = str(e).lower()
                logger.error(f"Erreur de connexion IMAP (tentative {attempt + 1}): {e}")
                
                # Vérifier si c'est un blocage temporaire
                if any(keyword in error_msg for keyword in ['eof', 'protocol', 'connection', 'timeout']):
                    if attempt < max_retries - 1:
                        logger.warning(f"Possible blocage temporaire détecté. Attente de {retry_delay}s avant nouvelle tentative...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error("Échec après toutes les tentatives. Possible blocage du serveur.")
                        logger.info("Suggestions:")
                        logger.info("1. Attendez quelques minutes/heures avant de relancer")
                        logger.info("2. Augmentez check_interval dans config.json")
                        logger.info("3. Vérifiez que votre IP n'est pas bloquée")
                        return False
                else:
                    # Erreur différente (credentials, etc.)
                    return False
            
        return False
    
    def decode_mime_words(self, text: str) -> str:
        """Décode les mots MIME encodés"""
        if text is None:
            return ""
        
        decoded_words = decode_header(text)
        decoded_text = ""
        
        for word, encoding in decoded_words:
            if isinstance(word, bytes):
                if encoding:
                    decoded_text += word.decode(encoding)
                else:
                    decoded_text += word.decode('utf-8', errors='ignore')
            else:
                decoded_text += word
        
        return decoded_text
    
    def check_email_filters(self, sender: str, subject: str, content: str) -> bool:
        """Vérifie si l'email correspond aux filtres configurés."""
        logger.info("=== FILTRAGE EMAIL ===")
        logger.info(f"Expéditeur: {sender}")
        logger.info(f"Sujet: {subject}")
        content_preview = content.strip()
        logger.info(f"Contenu (100 premiers caractères): {content_preview[:100]}...")

        # TEST TEMPORAIRE - mot magique pour forcer la détection
        if "TESTKEYWORDINC" in subject.upper() or "TESTKEYWORDINC" in content.upper():
            logger.info("🧪 Email accepté car mot-clé de test détecté")
            return True

        # 1. PRIORITÉ : Vérification des mots-clés (peu importe l'expéditeur)
        # Mots-clés dans le sujet
        subject_keywords = self.config['filters'].get('subject_keywords', [])
        logger.info(f"Vérification mots-clés sujet: {subject_keywords}")
        for keyword in subject_keywords:
            if keyword.lower() in subject.lower():
                logger.info(f"✅ Email accepté car mot-clé '{keyword}' trouvé dans le sujet")
                return True

        # Mots-clés dans le contenu du corps
        body_keywords = self.config['filters'].get('keywords', [])
        logger.info(f"Vérification mots-clés corps: {body_keywords}")
        for keyword in body_keywords:
            # Recherche insensible à la casse et même si collé à d'autres lettres
            if keyword.lower() in content.lower():
                logger.info(f"✅ Email accepté car mot-clé '{keyword}' trouvé dans le contenu")
                return True

        # 2. Vérification des expéditeurs autorisés
        allowed_senders = self.config['filters'].get('senders', [])
        logger.info(f"Vérification expéditeurs autorisés: {allowed_senders}")
        for allowed_sender in allowed_senders:
            if allowed_sender.lower() in sender.lower():
                logger.info(f"✅ Email accepté car expéditeur autorisé: {sender}")
                return True

        logger.info("❌ Email rejeté - aucun critère de filtre ne correspond")
        return False
    
    def get_email_content(self, msg) -> str:
        """Extrait le contenu textuel d'un email, en gérant le multipart et le HTML."""
        plain_text_content = ""
        html_content = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type not in ["text/plain", "text/html"]:
                    continue

                try:
                    payload = part.get_payload(decode=True)
                    if not payload:
                        continue
                    charset = part.get_content_charset() or 'utf-8'
                    decoded_payload = payload.decode(charset, errors='ignore')

                    if content_type == "text/plain":
                        plain_text_content += decoded_payload
                    elif content_type == "text/html":
                        html_content += decoded_payload
                except Exception as e:
                    logger.warning(f"Impossible de décoder une partie de l'email: {e}")
                    continue
        else:
            content_type = msg.get_content_type()
            if content_type in ["text/plain", "text/html"]:
                try:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        charset = msg.get_content_charset() or 'utf-8'
                        decoded_payload = payload.decode(charset, errors='ignore')
                        if content_type == "text/plain":
                            plain_text_content = decoded_payload
                        elif content_type == "text/html":
                            html_content = decoded_payload
                except Exception as e:
                    logger.warning(f"Impossible de décoder le contenu de l'email: {e}")

        if plain_text_content.strip():
            return plain_text_content

        if html_content:
            # Suppression des styles et scripts
            text_from_html = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            text_from_html = re.sub(r'<script[^>]*>.*?</script>', '', text_from_html, flags=re.DOTALL | re.IGNORECASE)
            # Suppression des autres balises HTML
            text_from_html = re.sub(r'<[^>]*>', '', text_from_html)
            # Nettoyage des lignes vides
            text_from_html = '\n'.join([line.strip() for line in text_from_html.splitlines() if line.strip()])
            return text_from_html

        return ""
    
    def check_new_emails(self) -> List[Dict]:
        """Vérifie les nouveaux emails"""
        try:
            # Recherche des emails non lus
            status, messages = self.imap.search(None, 'UNSEEN')
            
            if status != 'OK':
                logger.error("Erreur lors de la recherche d'emails")
                return []
            
            email_ids = messages[0].split()
            new_matching_emails = []
            
            for email_id in email_ids:
                try:
                    status, msg_data = self.imap.fetch(email_id, '(RFC822)')
                    
                    if status != 'OK':
                        continue
                    
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # Extraction des informations
                    sender = self.decode_mime_words(msg.get('From', ''))
                    subject = self.decode_mime_words(msg.get('Subject', ''))
                    date = msg.get('Date', '')
                    content = self.get_email_content(msg)
                    
                    # Vérification des filtres
                    if self.check_email_filters(sender, subject, content):
                        email_info = {
                            'id': email_id.decode(),
                            'sender': sender,
                            'subject': subject,
                            'date': date,
                            'content_preview': content[:200] + '...' if len(content) > 200 else content
                        }
                        new_matching_emails.append(email_info)
                        logger.info(f"Nouvel email correspondant trouvé: {subject} de {sender}")
                
                except Exception as e:
                    logger.error(f"Erreur lors du traitement de l'email {email_id}: {e}")
            
            return new_matching_emails
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des emails: {e}")
            return []
    
    def send_desktop_notification(self, email_info: Dict):
        """Envoie une notification desktop"""
        try:
            title = f"Nouveau mail: {email_info['subject'][:50]}"
            message = f"De: {email_info['sender']}\n{email_info['content_preview']}"
            
            subprocess.run([
                'notify-send',
                '-u', 'critical',
                '-t', '10000',
                title,
                message
            ], check=False)
            
        except Exception as e:
            logger.error(f"Erreur notification desktop: {e}")
    
    def play_sound_notification(self):
        """Joue un son d'alerte"""
        try:
            sound_file = self.config['notifications']['sound'].get('sound_file')
            if sound_file:
                subprocess.run(['aplay', sound_file], check=False, capture_output=True)
            else:
                # Son système par défaut
                subprocess.run(['pactl', 'upload-sample', '/usr/share/sounds/alsa/Front_Left.wav', 'bell'], check=False)
                subprocess.run(['pactl', 'play-sample', 'bell'], check=False)
                
        except Exception as e:
            logger.error(f"Erreur son d'alerte: {e}")
    
    def send_ntfy_notification(self, email_info: Dict):
        """Envoie une notification via ntfy.sh"""
        try:
            ntfy_config = self.config['notifications']['ntfy']
            
            # Extraire le nom de l'expéditeur (sans l'email complet)
            sender_name = email_info['sender'].split('<')[0].strip()
            if not sender_name:
                sender_name = email_info['sender'].split('@')[0]
            
            # Titre plus compact et joli
            title = f"✉️ {email_info['subject'][:40]}{'...' if len(email_info['subject']) > 40 else ''}"
            
            # Message structuré et lisible
            message = f"👤 **{sender_name}**\n\n"
            
            # Ajouter aperçu du contenu seulement s'il est informatif
            content_preview = email_info['content_preview'].strip()
            if content_preview and len(content_preview) > 10:
                # Nettoyer le contenu
                clean_content = content_preview.replace('\n', ' ').replace('\r', ' ')
                clean_content = ' '.join(clean_content.split())  # Supprimer espaces multiples
                message += f"💬 {clean_content[:100]}{'...' if len(clean_content) > 100 else ''}"
            
            data = {
                'title': title,
                'message': message,
                'priority': 5,  # Urgente
                'tags': ['📧', 'insa'],
                'click': 'https://partage.insa-lyon.fr'  # Lien vers votre webmail
            }
            
            response = requests.post(ntfy_config['url'], json=data, timeout=10)
            
            if response.status_code == 200:
                logger.info("Notification ntfy envoyée avec succès")
            else:
                logger.error(f"Erreur notification ntfy: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Erreur notification ntfy: {e}")
    
    def send_webhook_notification(self, email_info: Dict):
        """Envoie une notification via webhook"""
        try:
            webhook_config = self.config['notifications']['webhook']
            
            payload = {
                'type': 'new_email',
                'timestamp': datetime.now().isoformat(),
                'email': email_info
            }
            
            method = webhook_config.get('method', 'POST').upper()
            
            if method == 'POST':
                response = requests.post(webhook_config['url'], json=payload, timeout=10)
            elif method == 'GET':
                response = requests.get(webhook_config['url'], params=payload, timeout=10)
            
            if response.status_code < 300:
                logger.info("Notification webhook envoyée avec succès")
            else:
                logger.error(f"Erreur notification webhook: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Erreur notification webhook: {e}")
    
    def send_twilio_sms(self, email_info: Dict):
        """Envoie un SMS via Twilio"""
        try:
            from twilio.rest import Client
            
            twilio_config = self.config['notifications']['twilio']
            client = Client(twilio_config['account_sid'], twilio_config['auth_token'])
            
            message_body = f"📧 Nouveau mail urgent!\n\nDe: {email_info['sender']}\nSujet: {email_info['subject'][:100]}"
            
            message = client.messages.create(
                body=message_body,
                from_=twilio_config['from_number'],
                to=twilio_config['to_number']
            )
            
            logger.info(f"SMS Twilio envoyé: {message.sid}")
            
        except ImportError:
            logger.error("Bibliothèque Twilio non installée. Installez avec: pip install twilio")
        except Exception as e:
            logger.error(f"Erreur SMS Twilio: {e}")
    
    def send_whatsapp_callmebot(self, email_info: Dict):
        """Envoie un message WhatsApp via CallMeBot (gratuit)"""
        try:
            whatsapp_config = self.config['notifications']['whatsapp_callmebot']
            
            message = f"📧 *Nouveau mail urgent!*\n\n*De:* {email_info['sender']}\n*Sujet:* {email_info['subject'][:100]}\n\n{email_info['content_preview'][:200]}"
            
            # URL CallMeBot WhatsApp
            url = "https://api.callmebot.com/whatsapp.php"
            params = {
                'phone': whatsapp_config['phone_number'].replace('+', ''),
                'text': message,
                'apikey': whatsapp_config['api_key']
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if "Message queued" in response.text:
                logger.info("Message WhatsApp CallMeBot envoyé avec succès")
            else:
                logger.error(f"Erreur WhatsApp CallMeBot: {response.text}")
                
        except Exception as e:
            logger.error(f"Erreur WhatsApp CallMeBot: {e}")
    
    def send_whatsapp_twilio(self, email_info: Dict):
        """Envoie un message WhatsApp via Twilio"""
        try:
            from twilio.rest import Client
            
            whatsapp_config = self.config['notifications']['whatsapp_twilio']
            client = Client(whatsapp_config['account_sid'], whatsapp_config['auth_token'])
            
            message_body = f"📧 *Nouveau mail urgent!*\n\nDe: {email_info['sender']}\nSujet: {email_info['subject'][:100]}\n\n{email_info['content_preview'][:200]}"
            
            message = client.messages.create(
                body=message_body,
                from_=whatsapp_config['from_number'],
                to=whatsapp_config['to_number']
            )
            
            logger.info(f"WhatsApp Twilio envoyé: {message.sid}")
            
        except ImportError:
            logger.error("Bibliothèque Twilio non installée. Installez avec: pip install twilio")
        except Exception as e:
            logger.error(f"Erreur WhatsApp Twilio: {e}")
    
    def make_call_callmebot(self, email_info: Dict):
        """Effectue un appel vocal via CallMeBot"""
        try:
            call_config = self.config['notifications']['call_callmebot']
            
            # Message vocal
            message = f"Alerte email urgent de {email_info['sender']}. Sujet: {email_info['subject'][:50]}. Consultez votre boîte mail immédiatement."
            
            # URL CallMeBot Voice (format différent de WhatsApp)
            url = "https://api.callmebot.com/"
            params = {
                'user': call_config['phone_number'],
                'text': message
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if "Call queued" in response.text or response.status_code == 200:
                logger.info("Appel CallMeBot lancé avec succès")
            else:
                logger.error(f"Erreur appel CallMeBot: {response.text}")
                
        except Exception as e:
            logger.error(f"Erreur appel CallMeBot: {e}")
    
    def make_call_twilio(self, email_info: Dict):
        """Effectue un appel vocal via Twilio"""
        try:
            from twilio.rest import Client
            
            call_config = self.config['notifications']['call_twilio']
            client = Client(call_config['account_sid'], call_config['auth_token'])
            
            # Créer le message vocal
            twiml_message = f"<Response><Say voice='alice' language='fr-FR'>{call_config['message']} Email de {email_info['sender']}. Sujet: {email_info['subject'][:50]}.</Say></Response>"
            
            call = client.calls.create(
                to=call_config['to_number'],
                from_=call_config['from_number'],
                twiml=twiml_message
            )
            
            logger.info(f"Appel Twilio initié: {call.sid}")
            
        except ImportError:
            logger.error("Bibliothèque Twilio non installée. Installez avec: pip install twilio")
        except Exception as e:
            logger.error(f"Erreur appel Twilio: {e}")
    
    def make_call_freemobile(self, email_info: Dict):
        """Déclenche un appel via Free Mobile (France)"""
        try:
            call_config = self.config['notifications']['call_freemobile']
            
            # Free Mobile utilise un SMS spécial pour déclencher un appel
            message = f"APPEL URGENT: Email de {email_info['sender']}. Sujet: {email_info['subject'][:50]}. Consultez votre boîte mail."
            
            url = "https://smsapi.free-mobile.fr/sendmsg"
            params = {
                'user': call_config['user'],
                'pass': call_config['pass'],
                'msg': message
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                logger.info("Notification Free Mobile envoyée (déclenchera un appel/SMS)")
            else:
                logger.error(f"Erreur Free Mobile: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Erreur Free Mobile: {e}")
    
    def play_intensive_alarm(self, email_info: Dict):
        """Joue une alarme intensive répétée"""
        try:
            alarm_config = self.config['notifications']['alarm_intensive']
            repeat_count = alarm_config.get('repeat_count', 5)
            interval = alarm_config.get('interval_seconds', 2)
            sound_file = alarm_config.get('sound_file', '/usr/share/sounds/alsa/Front_Left.wav')
            
            logger.info(f"Déclenchement alarme intensive ({repeat_count}x) pour email urgent")
            
            for i in range(repeat_count):
                try:
                    # Son d'alarme
                    subprocess.run(['aplay', sound_file], check=False, capture_output=True)
                    
                    # Notification desktop répétée
                    subprocess.run([
                        'notify-send',
                        '-u', 'critical',
                        '-t', '5000',
                        '🚨 ALERTE EMAIL URGENT! 🚨',
                        f"({i+1}/{repeat_count}) {email_info['subject'][:30]}... DE: {email_info['sender']}"
                    ], check=False)
                    
                    if i < repeat_count - 1:  # Pas de pause après le dernier
                        time.sleep(interval)
                        
                except Exception as e:
                    logger.error(f"Erreur lors de l'alarme {i+1}: {e}")
                    
        except Exception as e:
            logger.error(f"Erreur alarme intensive: {e}")
    
    def send_notifications(self, email_info: Dict):
        """Envoie toutes les notifications configurées"""
        notifications_config = self.config['notifications']
        
        # Notification desktop
        if notifications_config['desktop']['enabled']:
            threading.Thread(target=self.send_desktop_notification, args=(email_info,)).start()
        
        # Son d'alerte
        if notifications_config['sound']['enabled']:
            threading.Thread(target=self.play_sound_notification).start()
        
        # Notification ntfy
        if notifications_config['ntfy']['enabled']:
            threading.Thread(target=self.send_ntfy_notification, args=(email_info,)).start()
        
        # Webhook
        if notifications_config['webhook']['enabled']:
            threading.Thread(target=self.send_webhook_notification, args=(email_info,)).start()
        
        # SMS Twilio
        if notifications_config['twilio']['enabled']:
            threading.Thread(target=self.send_twilio_sms, args=(email_info,)).start()
        
        # WhatsApp CallMeBot
        if notifications_config['whatsapp_callmebot']['enabled']:
            threading.Thread(target=self.send_whatsapp_callmebot, args=(email_info,)).start()
        
        # WhatsApp Twilio
        if notifications_config['whatsapp_twilio']['enabled']:
            threading.Thread(target=self.send_whatsapp_twilio, args=(email_info,)).start()
        
        # Appels téléphoniques
        if notifications_config['call_callmebot']['enabled']:
            threading.Thread(target=self.make_call_callmebot, args=(email_info,)).start()
        
        if notifications_config['call_twilio']['enabled']:
            threading.Thread(target=self.make_call_twilio, args=(email_info,)).start()
        
        if notifications_config['call_freemobile']['enabled']:
            threading.Thread(target=self.make_call_freemobile, args=(email_info,)).start()
        
        # Alarme intensive (comme un appel mais local)
        if notifications_config['alarm_intensive']['enabled']:
            threading.Thread(target=self.play_intensive_alarm, args=(email_info,)).start()
    
    def start_monitoring(self):
        """Démarre la surveillance des emails avec reconnexion automatique"""
        self.running = True
        check_interval = self.config['monitoring']['check_interval']
        connection_retries = 0
        max_connection_retries = 5
        
        logger.info(f"Surveillance démarrée (vérification toutes les {check_interval}s)")
        
        while self.running and connection_retries < max_connection_retries:
            try:
                # Vérifier/établir la connexion
                if not self.imap or connection_retries > 0:
                    if not self.connect_to_imap():
                        connection_retries += 1
                        logger.error(f"Échec de connexion {connection_retries}/{max_connection_retries}")
                        if connection_retries < max_connection_retries:
                            logger.info(f"Nouvelle tentative dans 60 secondes...")
                            time.sleep(60)
                            continue
                        else:
                            logger.error("Abandon après trop d'échecs de connexion")
                            break
                    else:
                        connection_retries = 0  # Reset counter on successful connection
                
                # Boucle principale de surveillance
                consecutive_errors = 0
                while self.running:
                    try:
                        new_emails = self.check_new_emails()
                        consecutive_errors = 0  # Reset error counter on success
                        
                        for email_info in new_emails:
                            logger.info(f"Email correspondant détecté: {email_info['subject']}")
                            self.send_notifications(email_info)
                        
                        time.sleep(check_interval)
                        
                    except Exception as e:
                        consecutive_errors += 1
                        error_msg = str(e).lower()
                        
                        # Erreurs de connexion - tenter de se reconnecter
                        if any(keyword in error_msg for keyword in ['eof', 'protocol', 'connection', 'timeout', 'socket']):
                            logger.warning(f"Erreur de connexion détectée ({consecutive_errors}/3): {e}")
                            if consecutive_errors >= 3:
                                logger.warning("Trop d'erreurs consécutives, tentative de reconnexion...")
                                break  # Sortir de la boucle interne pour se reconnecter
                            else:
                                logger.info(f"Attente de {check_interval * 2}s avant nouvelle tentative...")
                                time.sleep(check_interval * 2)
                        else:
                            # Autres erreurs
                            logger.error(f"Erreur dans la surveillance: {e}")
                            time.sleep(check_interval)
                            
            except KeyboardInterrupt:
                logger.info("Arrêt demandé par l'utilisateur")
                break
            except Exception as e:
                logger.error(f"Erreur fatale dans la surveillance: {e}")
                connection_retries += 1
                if connection_retries < max_connection_retries:
                    logger.info("Tentative de redémarrage...")
                    time.sleep(30)
                else:
                    break
        
        self.stop_monitoring()
    
    def stop_monitoring(self):
        """Arrête la surveillance"""
        self.running = False
        if self.imap:
            try:
                self.imap.close()
                self.imap.logout()
                logger.info("Connexion IMAP fermée")
            except:
                pass

def main():
    """Fonction principale"""
    monitor = EmailMonitor()
    
    try:
        monitor.start_monitoring()
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")

if __name__ == "__main__":
    main()
