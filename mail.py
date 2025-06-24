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
        """Se connecte au serveur IMAP Zimbra"""
        try:
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
            logger.error(f"Erreur de connexion IMAP: {e}")
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
        """Vérifie si l'email correspond aux filtres configurés"""
        # Vérification des expéditeurs (priorité absolue)
        for allowed_sender in self.config['filters']['senders']:
            if allowed_sender.lower() in sender.lower():
                logger.info(f"Email accepté car expéditeur autorisé: {sender}")
                return True
        
        # Vérification des mots-clés dans le sujet (seulement si expéditeur non autorisé)
        for keyword in self.config['filters']['subject_keywords']:
            if keyword.lower() in subject.lower():
                logger.info(f"Email accepté car mot-clé dans sujet: {keyword}")
                return True
        
        # Vérification des mots-clés dans le contenu (seulement si expéditeur non autorisé)
        for keyword in self.config['filters']['keywords']:
            if keyword.lower() in content.lower():
                logger.info(f"Email accepté car mot-clé dans contenu: {keyword}")
                return True
        
        return False
    
    def get_email_content(self, msg) -> str:
        """Extrait le contenu textuel d'un email"""
        content = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        content += payload.decode(charset, errors='ignore')
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                content = payload.decode(charset, errors='ignore')
        
        return content
    
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
        """Démarre la surveillance des emails"""
        if not self.connect_to_imap():
            return
        
        self.running = True
        check_interval = self.config['monitoring']['check_interval']
        
        logger.info(f"Surveillance démarrée (vérification toutes les {check_interval}s)")
        
        try:
            while self.running:
                new_emails = self.check_new_emails()
                
                for email_info in new_emails:
                    logger.info(f"Email correspondant détecté: {email_info['subject']}")
                    self.send_notifications(email_info)
                
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            logger.info("Arrêt demandé par l'utilisateur")
        except Exception as e:
            logger.error(f"Erreur dans la boucle de surveillance: {e}")
        finally:
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
