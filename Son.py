import paho.mqtt.client as mqtt
import pygame.mixer
import time
import json
import os

class Son:
    def __init__(self, broker="192.168.1.102", port=1883, topic="Tapis/sequence"):
        """
        Initialisation du lecteur de sons avec pygame
        """
        # Initialiser pygame.mixer pour l'audio
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)  # Augmenter le nombre de canaux audio disponibles
        
        # Configuration MQTT
        self.topic = topic
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        # Obtenir le chemin du dossier courant
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sounds_dir = os.path.join(current_dir, "son")
        
        # Dictionnaire pour stocker les sons préchargés
        self.sounds = {}
        
        # Charger tous les sons au démarrage
        for i in range(0, 6):
            try:
                sound_path = os.path.join(sounds_dir, f"son{i}.mp3")
                if os.path.exists(sound_path):
                    self.sounds[i] = pygame.mixer.Sound(sound_path)
                    print(f"Son {i} chargé avec succès")
                else:
                    print(f"Attention: Fichier son{i}.mp3 non trouvé dans {sound_path}")
            except Exception as e:
                print(f"Erreur lors du chargement du son {i}: {e}")
        
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
        """Callback appelé lors de la réception d'un message MQTT"""
        try:
            payload = msg.payload.decode()
            print(f"Message reçu: {payload}")
            data = json.loads(payload)
            
            if "couleur" in data and "pas" in data:
                sequence = data["couleur"]
                if data["pas"]:
                    sequence.append(5)
                self.play_sequence(sequence)
            else:
                print("Format du message incorrect")
            
        except Exception as e:
            print(f"Erreur lors du traitement du message: {e}")

    def play_sequence(self, sequence):
        """Joue une séquence de sons"""
        print(f"Lecture de la séquence: {sequence}")
        for number in sequence:
            if number in self.sounds:
                try:
                    print(f"Lecture du son {number}")
                    # Arrêter tous les sons en cours
                    pygame.mixer.stop()
                    # Jouer le nouveau son
                    self.sounds[number].play()
                    # Attendre que le son soit terminé
                    time.sleep(1.7)
                    if (number == 5):
                        time.sleep(2)
                except Exception as e:
                    print(f"Erreur lors de la lecture du son {number}: {e}")
            else:
                print(f"Son {number} non trouvé dans la bibliothèque")
            
    

    def stop(self):
        """Arrête proprement le lecteur"""
        pygame.mixer.stop()  # Arrête tous les sons
        pygame.mixer.quit()  # Ferme le système audio
        self.client.loop_stop()
        self.client.disconnect()
        print("Déconnexion du broker MQTT")

if __name__ == "__main__":
    mqtt_broker = "192.168.1.102"
    mqtt_port = 1883
    mqtt_topic = "Tapis/sequence"

    player = Son(broker=mqtt_broker, port=mqtt_port, topic=mqtt_topic)
    
    try:
        print("En attente de séquences... (Ctrl+C pour quitter)")
        while True:
            time.sleep(1.7)
    except KeyboardInterrupt:
        player.stop()
        print("Programme terminé")