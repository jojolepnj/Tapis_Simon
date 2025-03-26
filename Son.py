import paho.mqtt.client as mqtt
from playsound import playsound
import time
import json

class Son:
    def __init__(self, broker="192.168.1.102", port=1883, topic="Tapis/sequence"):
        """
        Args:
            broker (str): Adresse du broker MQTT
            port (int): Port du broker MQTT
            topic (str): Topic MQTT à écouter
        """
        # Configuration MQTT
        self.topic = topic
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        # Dictionnaire des sons disponibles
        self.sound_files = {
            0: "son0.mp3", # Vert
            1: "son1.mp3", # Rouge
            2: "son2.mp3", # Bleu 
            3: "son3.mp3", # Jaune
            4: "son4.mp3", # Erreur
            5: "son5.mp3"  # Le son ajouté si "pas" est True
        }
        
        # Connexion au broker MQTT
        try:
            self.client.connect(broker, port, 60)
            print(f"Connexion réussie au broker MQTT: {broker}:{port}")
        except Exception as e:
            print(f"Erreur de connexion au broker MQTT: {e}")
            
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        """Callback appelé lors de la connexion au broker MQTT"""
        if rc == 0:
            print(f"Connecté au topic: {self.topic}")
            client.subscribe(self.topic)
        else:
            print(f"Échec de connexion, code retour = {rc}")

    def on_message(self, client, userdata, msg):
        """
        Callback appelé lors de la réception d'un message MQTT
        
        Le message doit être un JSON avec une liste de chiffres et un booléen "pas"
        """
        try:
            # Décoder le message en JSON
            payload = msg.payload.decode()
            print(f"Message reçu: {payload}")
            data = json.loads(payload)
            
            if "couleur" in data and "pas" in data:
                sequence = data["couleur"]
                if data["pas"]:
                    sequence.append(5)  # Ajouter le son5 à la fin si "pas" est True
                self.play_sequence(sequence)
            else:
                print("Format du message incorrect")
            
        except Exception as e:
            print(f"Erreur lors du traitement du message: {e}")

    def play_sequence(self, sequence):
        """
        Joue une séquence de sons
        
        Args:
            sequence (list): Liste de chiffres correspondant aux sons à jouer
        """
        print(f"Lecture de la séquence: {sequence}")
        for number in sequence:
            if number in self.sound_files:
                try:
                    print(f"Lecture du son {number}")
                    playsound(self.sound_files[number])
                    time.sleep(0.4)  # Délai de 400 ms entre chaque son
                except Exception as e:
                    print(f"Erreur lors de la lecture du son {number}: {e}")
            else:
                print(f"Son {number} non trouvé dans la bibliothèque")

    def stop(self):
        """Arrête proprement le client MQTT"""
        self.client.loop_stop()
        self.client.disconnect()
        print("Déconnexion du broker MQTT")

if __name__ == "__main__":
    # Paramètres de configuration
    mqtt_broker = "192.168.1.102"
    mqtt_port = 1883
    mqtt_topic = "Tapis/sequence"

    # Initialiser et démarrer le lecteur de sons
    player = Son(broker=mqtt_broker, port=mqtt_port, topic=mqtt_topic)
    
    try:
        print("En attente de séquences... (Ctrl+C pour quitter)")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        player.stop()
        print("Programme terminé")