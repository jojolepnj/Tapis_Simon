import os
import time
import json
import pygame
import paho.mqtt.client as mqtt
from queue import Queue, Empty
from threading import Thread

class Son:
    def __init__(self, broker="10.0.200.9", port=1883, topic="Tapis/sequence", difficulty_topic="site/difficulte"):
        # Initialiser pygame.mixer pour l'audio
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)
        
        # Ajouter une queue pour les sons à jouer
        self.sound_queue = Queue()
        
        # Configuration MQTT
        self.topic = topic
        self.difficulty_topic = difficulty_topic
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
        
        # Variables pour la difficulté
        self.difficulty_level = 0  # 0=normal, 1=progressive, 2=accelerating
        self.base_display_time = 2  # Temps d'affichage de base (en secondes)
        
        # Connexion au broker MQTT
        try:
            self.client.connect(broker, port, 60)
            print(f"Connexion réussie au broker MQTT: {broker}:{port}")
        except Exception as e:
            print(f"Erreur de connexion au broker MQTT: {e}")
        
        # Démarrer le thread MQTT
        self.client.loop_start()
        
        # Démarrer le thread de lecture des sons
        self.running = True
        self.sound_thread = Thread(target=self._sound_worker, daemon=True)
        self.sound_thread.start()

    def _sound_worker(self):
        """Thread worker pour jouer les sons"""
        while self.running:
            try:
                sequence = self.sound_queue.get(timeout=0.1)
                self._play_sounds(sequence)
            except Empty:
                continue
            except Exception as e:
                print(f"Erreur dans le worker de son: {e}")

    def _play_sounds(self, sequence):
        """Joue une séquence de sons"""
        current_display_time = self.base_display_time
        for idx, number in enumerate(sequence):
            if number in self.sounds:
                try:
                    # Ajuster le délai en fonction de la difficulté
                    if self.difficulty_level == 1:  # Mode progressif
                        sequence_multiple = idx // 5
                        animation_speed_factor = 1.0 / (1 + (sequence_multiple * 0.2))  # Réduction de 20% tous les 5 sons
                        current_display_time = self.base_display_time * animation_speed_factor
                    elif self.difficulty_level == 2:  # Mode accéléré
                        animation_speed_factor = 1.0 / (1 + (idx * 0.1))  # Réduction de 10% à chaque son
                        current_display_time = self.base_display_time * animation_speed_factor

                    print(f"Lecture du son {number} avec un délai de {current_display_time:.2f} secondes")
                    pygame.mixer.stop()
                    self.sounds[number].play()
                    time.sleep(current_display_time)
                except Exception as e:
                    print(f"Erreur lors de la lecture du son {number}: {e}")
            else:
                print(f"Son {number} non trouvé dans la bibliothèque")

    def play_sequence(self, sequence):
        """Ajoute une séquence de sons à la queue"""
        self.sound_queue.put(sequence)

    def on_message(self, client, userdata, msg):
        """Callback appelé lors de la réception d'un message MQTT"""
        try:
            payload = msg.payload.decode()
            print(f"Message reçu sur le topic {msg.topic}: {payload}")
            data = json.loads(payload)
            
            if msg.topic == self.difficulty_topic:
                # Gestion des messages de difficulté
                if "dif" in data:
                    new_difficulty = data["dif"]
                    if 0 <= new_difficulty <= 2:
                        self.difficulty_level = new_difficulty
                        print(f"Niveau de difficulté mis à jour: {self.difficulty_level}")
                    else:
                        print("Valeur de difficulté invalide")
            elif msg.topic == self.topic:
                # Gestion des messages de séquence
                if "couleur" in data and "pas" in data:
                    sequence = data["couleur"]
                    if data["pas"]:
                        sequence.insert(0, 5)
                        sequence.append(5)
                    self.play_sequence(sequence)
                else:
                    print("Format du message incorrect")
        except Exception as e:
            print(f"Erreur lors du traitement du message: {e}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connecté aux topics: {self.topic}, {self.difficulty_topic}")
            client.subscribe(self.topic)
            client.subscribe(self.difficulty_topic)
        else:
            print(f"Échec de connexion, code retour = {rc}")

    def stop(self):
        """Arrête proprement le lecteur"""
        self.running = False
        if self.sound_thread.is_alive():
            self.sound_thread.join(timeout=1)
        pygame.mixer.stop()
        pygame.mixer.quit()
        self.client.loop_stop()
        self.client.disconnect()
        print("Déconnexion du broker MQTT")