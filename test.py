import paho.mqtt.client as mqtt
import time
import json

def on_connect(client, userdata, flags, rc):
    print(f"Connecté avec le code: {rc}")
    if rc == 0:
        print("Connexion réussie!")
        # Publier le message de démarrage
        print("Publication du message 'true' sur site/start...")
        client.publish("site/start", "true")
        print("Message de démarrage publié!")
        
        # Attendre un peu avant d'envoyer la difficulté
        time.sleep(1)
        
        # Publier la difficulté facile (0)
        difficulty_message = json.dumps({'dif': 2})  # 0 = facile
        print(f"Publication de la difficulté sur site/difficulte: {difficulty_message}")
        client.publish("site/difficulte", difficulty_message)
        print("Message de difficulté publié!")

# Créer un nouveau client
client = mqtt.Client()
client.on_connect = on_connect

try:
    # Se connecter au broker
    print("Tentative de connexion au broker MQTT...")
    client.connect("10.0.200.7", 1883, 60)
    
    # Démarrer la boucle
    client.loop_start()
    
    # Attendre un peu pour s'assurer que les messages sont envoyés
    time.sleep(2)
    
    # Arrêter proprement
    client.loop_stop()
    client.disconnect()
    print("\nDéconnexion effectuée")

except Exception as e:
    print(f"Erreur: {str(e)}")