#!/usr/bin/env python3
import json

print("🔍 Test de la configuration")

try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print("✅ Fichier config.json chargé avec succès")
    
    print("\n📧 Configuration email:")
    print(f"  Serveur: {config['email']['server']}")
    print(f"  Username: {config['email']['username']}")
    
    print("\n🔍 Filtres configurés:")
    print(f"  Expéditeurs autorisés: {config['filters']['senders']}")
    print(f"  Mots-clés sujet: {config['filters']['subject_keywords']}")
    print(f"  Mots-clés contenu: {config['filters']['keywords']}")
    
    print("\n🔔 Notifications activées:")
    for service, settings in config['notifications'].items():
        if isinstance(settings, dict) and settings.get('enabled'):
            print(f"  ✅ {service}")
        elif isinstance(settings, dict):
            print(f"  ❌ {service}")
    
    print("\n⏱️ Monitoring:")
    print(f"  Intervalle: {config['monitoring']['check_interval']}s")
    print(f"  Boîte mail: {config['monitoring']['mailbox']}")
    
except FileNotFoundError:
    print("❌ Fichier config.json non trouvé")
except json.JSONDecodeError as e:
    print(f"❌ Erreur de syntaxe JSON: {e}")
except Exception as e:
    print(f"❌ Erreur: {e}") 