from datetime import datetime
from queue import Queue, Empty 
from threading import Event, Thread

import random
import socketio
import paho.mqtt.client as mqtt
import json
import sys
import time
import os
import pygame.mixer
import msvcrt

class Son:
    def __init__(self, broker="192.168.1.102", port=1883, topic="Tapis/sequence"):
        # Initialiser pygame.mixer pour l'audio
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)
        
        # Ajouter une queue pour les sons à jouer
        self.sound_queue = Queue()
        
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
        for number in sequence:
            if number in self.sounds:
                try:
                    print(f"Lecture du son {number}")
                    pygame.mixer.stop()
                    self.sounds[number].play()
                    time.sleep(2)
                    if number == 5:
                        time.sleep(2)
                    if number == 2:
                        time.sleep(0.5)
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

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connecté au topic: {self.topic}")
            client.subscribe(self.topic)
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
class JeuSimon:
    """
    Classe principale du jeu Simon.
    Gère la logique du jeu et la communication avec le SensFloor.
    """

    def __init__(self, mode_test=False):
        self.difficulte = "facile"
        
        self.config_difficulte = {
            "facile": {
                "temps_attente": 100.0,     # 20 secondes par couleur (augmenté)
                "nouvelles_couleurs": 1,    # Ajoute 1 couleur par tour
                "temps_sequence": 0.0,      # Pas de délai entre les couleurs
                "delai_entre_tours": 1.0    # Pas de délai entre les tours
            },
            "moyen": {
                "temps_attente": 70.0,      # 15 secondes par couleur (augmenté)
                "nouvelles_couleurs": 1,    # Ajoute 1 couleur par tour
                "temps_sequence": 0.0,      # Pas de délai entre les couleurs
                "delai_entre_tours": 1.0    # Pas de délai entre les tours
            },
            "difficile": {
                "temps_attente": 50.0,      # 10 secondes par couleur (augmenté)
                "nouvelles_couleurs": 2,    # Ajoute 2 couleurs par tour
                "temps_sequence": 0.0,      # Pas de délai entre les couleurs
                "delai_entre_tours": 1.0    # Pas de délai entre les tours
            }
        }
        self.mode_test = mode_test
        self.current_mode = "test" if mode_test else "normal"
        
        self.couleur_vers_chiffre = {
            'vert': 0,
            'rouge': 1,
            'bleu': 2,
            'jaune': 3
        }
        self.chiffre_vers_couleur = {
            0: 'vert',
            1: 'rouge',
            2: 'bleu',
            3: 'jaune'
        }
        # Configuration MQTT
        self.mqtt_client = mqtt.Client()
        self.mqtt_broker = "192.168.1.102"
        self.mqtt_port = 1883
        self.mqtt_topic = "Tapis/sequence"
        self.led_status_topic = "LED/status"
        self.start_topic = "site/start"  # Topic pour démarrer le jeu
        self.game_started = False
        
        # Configure le callback pour la réception des messages
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.on_subscribe = self.on_subscribe  # Nouveau callback pour les abonnements
        self.mqtt_client.on_connect = self.on_connect 

        # Initialize MQTT connection
        self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port)
        self.mqtt_client.subscribe([(self.led_status_topic, 0), (self.start_topic, 0)])
        self.mqtt_client.loop_start()

        # Création du client socket pour la communication réseau
        self.socket = socketio.Client(
            reconnection_delay=1,
            reconnection=True,
            reconnection_attempts=5,
            reconnection_delay_max=5,
            logger=False,
            engineio_logger=False
        )

        # Création de l'état du jeu
        self.etat = EtatJeu()
        
        # Configuration des événements socket
        self._config_socket()

        # Démarrage du thread de surveillance des commandes
        self.running = True
        self.command_thread = Thread(target=self.mode_switch_monitor, daemon=True)
        self.command_thread.start()

        self.sound_manager = Son()

    def afficher_parametres_difficulte(self):
        """Affiche les paramètres du niveau de difficulté actuel"""
        config = self.config_difficulte[self.difficulte]
        print("\nParamètres actuels :")
        print(f"- Temps pour reproduire chaque couleur : {config['temps_attente']} secondes")
        print(f"- Nouvelles couleurs par tour : {config['nouvelles_couleurs']}")
        print(f"- Temps entre chaque couleur : {config['temps_sequence']} secondes")
        print(f"- Délai entre les tours : {config['delai_entre_tours']} secondes")
    def on_connect(self, client, userdata, flags, rc):
        """Callback appelé lors de la connexion au broker MQTT"""
        connection_status = {
            0: "Connection successful",
            1: "Connection refused - incorrect protocol version",
            2: "Connection refused - invalid client identifier",
            3: "Connection refused - server unavailable",
            4: "Connection refused - bad username or password",
            5: "Connection refused - not authorized"
        }
        if rc == 0:
            print(f"MQTT Connection established: {connection_status.get(rc, 'Unknown status')}")
            # Réabonnement aux topics en cas de reconnexion
            client.subscribe([(self.led_status_topic, 0), (self.start_topic, 0)])
        else:
            print(f"MQTT Connection failed: {connection_status.get(rc, 'Unknown error')}")
    def on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback appelé lors de l'abonnement à un topic"""
        print(f"Successfully subscribed to topics with QoS: {granted_qos}")
    def mode_switch_monitor(self):
        """Monitor for mode switch commands"""
        while self.running:
            try:
                if not hasattr(self, 'in_test_sequence') or not self.in_test_sequence:
                    if self.mode_test:
                        command = input("\nEnter 'm' to switch to normal mode, 'q' to quit: ").lower()
                        if command == 'm':
                            self.switch_mode()
                        elif command == 'q':
                            self.running = False
                            sys.exit(0)
                    else:
                        command = input("\nEnter 'q' to quit: ").lower()
                        if command == 'q':
                            self.running = False
                            sys.exit(0)
                time.sleep(0.1)
            except Exception as e:
                print(f"Command error: {e}")
                break

    def switch_mode(self):
        """Switch between test and normal mode"""
        self.mode_test = not self.mode_test
        self.current_mode = "test" if self.mode_test else "normal"
        
        if self.mode_test:
            if hasattr(self, 'socket') and self.socket.connected:
                self.socket.disconnect()
            print("Switched to TEST mode")
        else:
            try:
                self.socket.connect(
                    'http://192.168.5.5:8000',
                    transports=['websocket'],
                    wait=True,
                    wait_timeout=10
                )
                print("Switched to NORMAL mode")
            except Exception as e:
                print(f"Failed to connect to server: {e}")
                print("Falling back to TEST mode")
                self.mode_test = True
                self.current_mode = "test"

    # Add method for test mode simulation
    def mode_test_simuler_pas(self):
        """Version modifiée pour prendre en compte la difficulté"""
        config = self.config_difficulte[self.difficulte]
        print("\nMode Test - Séquence à reproduire :")
        for i, couleur in enumerate(self.etat.sequence, 1):
            print(f"{i}. {couleur} ({self.couleur_vers_chiffre[couleur]})")
        
        self.etat.preparer_tour()
        derniere_couleur = None
        sequence_joueur = []
        
        while self.etat.position < len(self.etat.sequence):
            try:
                print(f"\nEntrez la couleur {self.etat.position + 1}/{len(self.etat.sequence)}")
                print("(0:vert, 1:rouge, 2:bleu, 3:jaune, q:quit)")
                print("> ", end='', flush=True)  # Affiche le prompt sans nouvelle ligne
                
                # Démarre le chrono après avoir affiché le prompt
                start_time = time.time()
                choix = input().lower()  # Enlève le prompt ">" de input()
                elapsed_time = time.time() - start_time
                
                if choix == 'q':
                    raise Exception("Test mode terminated")
                
                if choix in ['0', '1', '2', '3']:
                    # Vérifie le temps APRÈS avoir reçu une réponse valide
                    if elapsed_time > config['temps_attente']:
                        print(f"\nTemps écoulé ! Vous avez dépassé {config['temps_attente']} secondes.")
                        return False
                    
                    couleur = self.chiffre_vers_couleur[int(choix)]
                    
                    if couleur == derniere_couleur:
                        print("Même couleur que la précédente, ignorée")
                        continue
                        
                    derniere_couleur = couleur
                    sequence_joueur.append(couleur)
                    self.etat.ajouter_couleur(couleur)
                    print(f"Couleur ajoutée : {couleur}")
                    
                    message = {
                        "couleur": [self.couleur_vers_chiffre[couleur]],
                        "pas": False
                    }
                    self.mqtt_client.publish(self.mqtt_topic, json.dumps(message))
                    print(f"MQTT >>> [Tapis/sequence] Mode test - Couleur jouée : {json.dumps(message)}")
                    
                    if couleur != self.etat.sequence[self.etat.position - 1]:
                        print(f"\nErreur! Couleur attendue : {self.etat.sequence[self.etat.position - 1]}")
                        return False
                        
                else:
                    print("Entrée invalide. Utilisez 0-3 ou q pour quitter")
                    
            except Exception as e:
                print(f"Erreur mode test : {e}")
                return False
        
        if sequence_joueur == self.etat.sequence:
            print("\nBravo! Séquence complétée avec succès!")
            return True
        return False
        
    def convertir_sequence_en_chiffres(self, sequence):
        """Convertit une séquence de couleurs en séquence de chiffres"""
        return [self.couleur_vers_chiffre[couleur] for couleur in sequence]

    def on_mqtt_message(self, client, userdata, message):
        """Callback appelé quand un message MQTT est reçu"""
        try:
            topic = message.topic
            payload = message.payload.decode()
            timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            
            if topic == self.start_topic:
                print(f"[{timestamp}] Message reçu sur {topic}:")
                print(f"  └─ Payload: {payload}")
                print(f"  └─ QoS: {message.qos}")
                print(f"  └─ Retain Flag: {message.retain}")
                
                try:
                    if payload.lower() == "true" and not self.game_started:
                        print(f"  └─ Action: Démarrage du jeu")
                        self.game_started = True
                        game_thread = Thread(target=self.demarrer, daemon=True)
                        game_thread.start()
                    elif payload.lower() == "true" and self.game_started:
                        print(f"  └─ Action: Ignoré (jeu déjà en cours)")
                    else:
                        print(f"  └─ Action: Aucune (payload différent de 'true')")
                except Exception as e:
                    print(f"  └─ Erreur lors du traitement du message: {e}")
                    
            elif topic == self.led_status_topic:
                try:
                    if payload.lower() == "true" and not self.game_started:
                        print("\nMessage de démarrage reçu sur site/start")
                        self.game_started = True
                        game_thread = Thread(target=self.demarrer, daemon=True)
                        game_thread.start()
                except Exception as e:
                    print(f"Error processing start message: {e}")
            
        except Exception as e:
            print(f"Error processing MQTT message: {e}")
    def publier_sequence_mqtt(self, sequence, tmp, index, type_sequence="generated"):
        """
        Publie la séquence sur le topic MQTT
        Convertit les couleurs en chiffres avant l'envoi
        """
        try:
            if tmp == 3:  # Error case
                error_message = {
                    "couleur": [4],
                    "pas": False
                }
                self.mqtt_client.publish(self.mqtt_topic, json.dumps(error_message))
                print(f"Error sequence published to MQTT: {error_message}")
                return

            sequence_chiffres = self.convertir_sequence_en_chiffres(sequence)
            if tmp == 2:  # Full sequence case
                message = {
                    "couleur": sequence_chiffres,
                    "pas": True
                }
                print(f"MQTT >>> [Tapis/sequence] Séquence complète : {json.dumps(message)}")
            elif tmp == 1:  # Single color case
                message = {
                    "couleur": [self.couleur_vers_chiffre[couleur]],  # Mettre le nombre dans une liste
                    "pas": False
                }
                print(f"MQTT >>> [Tapis/sequence] Couleur unique : {json.dumps(message)}")
            
            self.mqtt_client.publish(self.mqtt_topic, json.dumps(message))
            print(f"Sequence published to MQTT: {message}")
            
        except Exception as e:
            error_message = {
                "couleur": [4],
                "pas": False
            }
            self.mqtt_client.publish(self.mqtt_topic, json.dumps(error_message))
            print(f"Failed to publish to MQTT: {e}")
            print(f"Sent error sequence: {error_message}")
    def montrer_sequence(self, temps_sequence):
        """Montre la séquence de couleurs avec son"""
        print("\nAttention ! Voici la séquence :")
        
        # Envoyer la séquence une seule fois avec le son de fin (5)
        sequence_chiffres = [self.couleur_vers_chiffre[c] for c in self.etat.sequence]
        sequence_message = {
            "couleur": sequence_chiffres,
            "pas": True  # Cela ajoutera automatiquement le son 5 à la fin
        }
        self.mqtt_client.publish(self.mqtt_topic, json.dumps(sequence_message))
        print(f"MQTT >>> [Tapis/sequence] Séquence envoyée : {json.dumps(sequence_message)}")
        
        # Afficher simplement la séquence sans jouer les sons
        for i, couleur in enumerate(self.etat.sequence, 1):
            chiffre = self.couleur_vers_chiffre[couleur]
            print(f"{i}. {couleur} ({chiffre})")
            time.sleep(2)  # Attendre que le son soit joué

    def _config_socket(self):
        """Configure les événements de connexion socket."""
        
        @self.socket.event
        def connect():
            """Appelé quand la connexion est établie."""
            print("Connecté au serveur SensFloor")
            self.socket.eio.ping_timeout = 2000  # 2 seconds

        @self.socket.event
        def disconnect():
            """Appelé quand la connexion est perdue."""
            print("Déconnecté du serveur")
            if not self.etat.peut_jouer:
                self.etat.peut_jouer = True
                print("Forçage de la reprise du jeu après déconnexion")

        @self.socket.on('step')
        def on_pas(x, y):
            """Appelé quand un pas est détecté sur le SensFloor."""
            self.traiter_pas(x, y)
            
        @self.socket.on('objects-update')
        def on_objects_update(objects):
            if isinstance(objects, list):
                self.etat.peut_jouer = True
                #print("Détection des pas activée pour nouvelle séquence")
    def creer_sequence(self, seq_precedente):
        """Crée une nouvelle séquence de couleurs et la publie via MQTT."""
        couleurs = ['vert', 'rouge', 'bleu', 'jaune']
        if seq_precedente:
            # Évite de répéter la dernière couleur
            couleurs = [c for c in couleurs if c != seq_precedente[-1]]
        nouvelle_sequence = seq_precedente + [random.choice(couleurs)]
        # On ne publie plus la séquence ici
        return nouvelle_sequence

    def afficher_sequence(self, sequence):
        """Affiche la séquence que le joueur doit reproduire avec les chiffres correspondants."""
        print("\nSéquence à reproduire :")
        for i, couleur in enumerate(sequence, 1):
            chiffre = self.couleur_vers_chiffre[couleur]
            print(f"{i}. {couleur} ({chiffre})")
        print("\n")

    def detecter_couleur(self, x, y):
        """
        Convertit les coordonnées du pas en couleur.
        Le SensFloor est divisé en 4 zones de couleur.
        """
        if 0 <= x <= 0.5:
            return 'vert' if 0 <= y <= 0.5 else 'rouge'
        elif 0.5 < x <= 1:
            return 'jaune' if 0 <= y <= 0.5 else 'bleu'
        return 'inconnu'
    def reinitialiser_queue_couleurs(self):
        """Vide la queue des couleurs"""
        while not self.etat.couleurs.empty():
            self.etat.couleurs.get()
    def traiter_pas(self, x, y):
        """Traite un nouveau pas détecté sur le SensFloor."""
        if not self.etat.peut_jouer:
            return

        try:
            x, y = float(x), float(y)
            print(f"Pas détecté en : ({x}, {y})")
            
            couleur = self.detecter_couleur(x, y)
            if couleur == 'inconnu':
                return
                
            print(f"Couleur détectée : {couleur}")
            
            temps_actuel = time.time()
            if not hasattr(self, 'dernier_pas') or temps_actuel - self.dernier_pas > 0.5:
                print(f"Nouvelle couleur : {couleur}")
                self.etat.ajouter_couleur(couleur)
                self.dernier_pas = temps_actuel
                
                # Envoyer la couleur détectée en MQTT uniquement
                chiffre = self.couleur_vers_chiffre[couleur]
                message = {
                    "couleur": [chiffre],
                    "pas": False
                }
                self.mqtt_client.publish(self.mqtt_topic, json.dumps(message))
                print(f"MQTT >>> [Tapis/sequence] Détection pas : {json.dumps(message)}")
                
        except Exception as e:
            print(f"Erreur : {str(e)}")           
    def attendre_fin_pas(self, timeout=1.0):
        """Attend que le joueur ne soit plus sur une zone."""
        self.etat.pas_en_cours.clear()
        # Attend un court instant pour voir si un nouveau pas est détecté
        is_stepping = self.etat.pas_en_cours.wait(timeout)
        return not is_stepping
    def envoyer_erreur_mqtt(self, type_erreur="sequence"):
        """Envoie un message d'erreur via MQTT"""
        error_message = {
            "couleur": [4],  # 4 représente une erreur
            "pas": False
        }
        time.sleep(1)
        self.mqtt_client.publish(self.mqtt_topic, json.dumps(error_message))
        
        print(f"MQTT >>> Envoi signal d'erreur : {error_message}")

    def stop(self):
        """Arrête proprement le jeu"""
        print("Arrêt du jeu demandé")
        self.game_started = False
        if hasattr(self, 'sound_manager'):
            self.sound_manager.stop()
        if hasattr(self, 'mqtt_client'):
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            print("Déconnexion du broker MQTT effectuée")
        print("Arrêt du jeu terminé")
    def lire_sequence_test(self, longueur_sequence, temps_total):
        """Gestion du mode test avec vérification du temps"""
        sequence_joueur = []
        sequence_start_time = time.time()
        self.in_test_sequence = True  # Indiquer que nous sommes en séquence de test
        
        try:
            for position in range(longueur_sequence):
                temps_ecoule = time.time() - sequence_start_time
                temps_restant = temps_total - temps_ecoule
                
                if temps_restant <= 0:
                    self.envoyer_erreur_mqtt("timeout")
                    print(f"\nTemps écoulé ! Vous avez dépassé {temps_total} secondes.")
                    self.sound_manager.play_sequence([4])
                    return None
                
                print(f"\nEntrez la couleur {position + 1}/{longueur_sequence}")
                print("(0:vert, 1:rouge, 2:bleu, 3:jaune, q:quit)")
                print(f"Temps restant : {temps_restant:.1f} secondes")
                print("> ", end='', flush=True)
                
                # Utiliser un timeout pour input
                start_input_time = time.time()
                choix = None
                
                while True:
                    if msvcrt.kbhit():
                        char = msvcrt.getch().decode('utf-8').lower()
                        if char in ['0', '1', '2', '3', 'q']:
                            choix = char
                            print(char)  # Afficher le caractère saisi
                            break
                    
                    current_time = time.time()
                    temps_ecoule = current_time - sequence_start_time
                    temps_restant = temps_total - temps_ecoule
                    
                    if temps_restant <= 0:
                        print(f"\nTemps écoulé ! Vous avez dépassé {temps_total} secondes.")
                        self.envoyer_erreur_mqtt("timeout")
                        self.sound_manager.play_sequence([4])
                        return None
                    
                    # Mise à jour du temps toutes les 0.5 secondes
                    if int(temps_restant * 2) != int((temps_total - (current_time - start_input_time)) * 2):
                        print(f"\rTemps restant : {temps_restant:.1f} secondes > ", end='', flush=True)
                    
                    time.sleep(0.1)
                
                if choix == 'q':
                    self.envoyer_erreur_mqtt("abandon")
                    print("\nPartie abandonnée.")
                    return None
                
                couleur = self.chiffre_vers_couleur[int(choix)]
                sequence_joueur.append(couleur)
                
                # Vérifier si la couleur est correcte
                if couleur != self.etat.sequence[position]:
                    message = {
                        "couleur": [self.couleur_vers_chiffre[couleur]],
                        "pas": False
                    }
                    self.mqtt_client.publish(self.mqtt_topic, json.dumps(message))
                    self.envoyer_erreur_mqtt("wrong_color")
                    print(f"\nErreur ! Couleur attendue : {self.etat.sequence[position]}")
                    print(f"Couleur reçue : {couleur}")
                    return None
                
                # Si la couleur est correcte, envoie la confirmation
                message = {
                    "couleur": [self.couleur_vers_chiffre[couleur]],
                    "pas": False
                }
                self.mqtt_client.publish(self.mqtt_topic, json.dumps(message))
                print(f"MQTT >>> [Tapis/sequence] Lecture test : {json.dumps(message)}")
            
            return sequence_joueur
        
        finally:
            self.in_test_sequence = False  # Réinitialiser le flag quoi qu'il arrive

    def lire_sequence_tapis(self, longueur_sequence, temps_total):
        """Gestion du mode normal avec le tapis"""
        sequence_joueur = []
        self.etat.peut_jouer = True
        position = 0
        sequence_start_time = time.time()  # Ajout de cette ligne
        
        while position < longueur_sequence:
            # Afficher le temps restant
            temps_ecoule = time.time() - sequence_start_time
            temps_restant = temps_total - temps_ecoule
            print(f"\rTemps restant : {temps_restant:.1f} secondes", end='', flush=True)
            
            if temps_restant <= 0:
                self.envoyer_erreur_mqtt("timeout")
                print(f"\nTemps total écoulé ! Vous avez dépassé {temps_total} secondes.")
                self.sound_manager.play_sequence([4])  # Jouer le son d'erreur
                return None
                
            if len(self.etat.couleurs.queue) > 0:
                couleur = self.etat.couleurs.get()
                sequence_joueur.append(couleur)
                
                # Vérifier si la couleur est correcte
                if couleur != self.etat.sequence[position]:
                    message = {
                        "couleur": [self.couleur_vers_chiffre[couleur]],
                        "pas": False
                    }
                    self.mqtt_client.publish(self.mqtt_topic, json.dumps(message))
                    print(f"MQTT >>> [Tapis/sequence] Lecture normale : {json.dumps(message)}")
                    self.envoyer_erreur_mqtt("wrong_color")
                    print(f"\nErreur ! Couleur attendue : {self.etat.sequence[position]}")
                    print(f"Couleur reçue : {couleur}")
                    self.sound_manager.play_sequence([4])  # Jouer le son d'erreur
                    return None
                    
                position += 1
                
            time.sleep(0.1)  # Petite pause pour ne pas surcharger le CPU
            
        return sequence_joueur
    def lire_sequence_joueur(self, longueur_sequence):
        """Lit la séquence entrée par le joueur selon le mode de jeu"""
        config = self.config_difficulte[self.difficulte]
        
        # Le temps d'attente total est le temps par couleur multiplié par le nombre de couleurs
        temps_total = config['temps_attente'] * longueur_sequence
        
        print(f"\nTemps disponible pour cette séquence : {temps_total} secondes")
        
        # On garde le temps_attente original et on crée un temps_total pour cette séquence
        if self.mode_test:
            return self.lire_sequence_test(longueur_sequence, temps_total)
        else:
            return self.lire_sequence_tapis(longueur_sequence, temps_total)
    def changer_difficulte(self, nouvelle_difficulte):
        """Change le niveau de difficulté du jeu"""
        if nouvelle_difficulte in self.config_difficulte:
            self.difficulte = nouvelle_difficulte
            print(f"\nNiveau de difficulté changé à : {nouvelle_difficulte}")
            self.afficher_parametres_difficulte()
        else:
            print("Niveau de difficulté invalide. Choisissez entre : facile, moyen, difficile")


    def demarrer_jeu(self):
        """Gère une partie avec les paramètres de difficulté"""
        config = self.config_difficulte[self.difficulte]
        self.etat.sequence = []
        score = 0
        derniere_couleur = None
        
        print("\n=== Début des messages MQTT ===")
        
        while True:
            # Réinitialiser pour la nouvelle séquence
            self.etat.peut_jouer = False
            self.reinitialiser_queue_couleurs()
            
            # Générer la nouvelle séquence
            for _ in range(config['nouvelles_couleurs']):
                couleurs_disponibles = [c for c in self.couleur_vers_chiffre.keys()
                                    if c != derniere_couleur]
                nouvelle_couleur = random.choice(couleurs_disponibles)
                derniere_couleur = nouvelle_couleur
                self.etat.sequence.append(nouvelle_couleur)
            
            print("\nNouvelle séquence :")
            self.montrer_sequence(config['temps_sequence'])
            time.sleep(config['delai_entre_tours'])
            
            # Lire la séquence du joueur
            sequence_joueur = self.lire_sequence_joueur(len(self.etat.sequence))
            if sequence_joueur is None:
                # Ne pas jouer le son ici, il sera joué via MQTT
                break
            
            if sequence_joueur == self.etat.sequence:
                score += len(sequence_joueur)
                # Envoyer le son de succès via MQTT
                message = {
                    "couleur": [5],
                    "pas": False
                }
                #self.mqtt_client.publish(self.mqtt_topic, json.dumps(message))
                print(f"\nBravo ! Score actuel : {score}")
            else:
                # Ne pas jouer le son ici, il sera joué via MQTT
                break
        
        print(f"\nPartie terminée. Score final : {score}")      
    def choisir_difficulte_avec_tapis(self):
        """Permet de choisir la difficulté en utilisant le tapis"""
        print("\nChoisissez la difficulté en marchant sur une couleur :")
        print("VERT   : Mode Facile")
        print("ROUGE  : Mode Moyen")
        print("BLEU   : Mode Difficile")
        
        self.etat.peut_jouer = True
        choix_fait = Event()
        self.difficulte = None
        
        # Créer une fonction pour gérer la détection des couleurs
        def on_couleur_detectee(x, y):
            if not choix_fait.is_set():
                couleur = self.detecter_couleur(x, y)
                if couleur == 'vert':
                    self.difficulte = "facile"
                    choix_fait.set()
                elif couleur == 'rouge':
                    self.difficulte = "moyen"
                    choix_fait.set()
                elif couleur == 'bleu':
                    self.difficulte = "difficile"
                    choix_fait.set()
                
                if choix_fait.is_set():
                    # Envoyer la couleur choisie en MQTT
                    message = {
                        "couleur": [self.couleur_vers_chiffre[couleur]],
                        "pas": False
                    }
                    self.mqtt_client.publish(self.mqtt_topic, json.dumps(message))
                    print(f"MQTT >>> [Tapis/sequence] Choix difficulté : {json.dumps(message)}")
                    print(f"\nDifficulté choisie : {self.difficulte}")
                    self.afficher_parametres_difficulte()
        
        # Enregistrer le handler temporaire pour les pas
        @self.socket.on('step')
        def on_step(x, y):
            on_couleur_detectee(x, y)
        
        # Attendre le choix avec un timeout
        try:
            if not choix_fait.wait(timeout=30):  # Timeout de 30 secondes
                print("\nAucun choix fait dans le temps imparti. Passage en mode facile par défaut.")
                self.difficulte = "facile"
        except Exception as e:
            print(f"Erreur lors de la détection : {e}")
            self.difficulte = "facile"  # Mode par défaut en cas d'erreur
        finally:
            # Réinitialiser le handler des pas pour le jeu normal
            @self.socket.on('step')
            def on_pas(x, y):
                self.traiter_pas(x, y)
        
        return self.difficulte
    def choisir_difficulte_manuelle(self):
        """Permet de choisir la difficulté manuellement"""
        print("Choisissez votre niveau de difficulté :")
        print("1. Facile - Recommandé pour débuter")
        print("2. Moyen  - Pour les joueurs habitués")
        print("3. Difficile - Pour les experts")
        
        while True:
            choix = input("\nVotre choix (1-3) : ").strip()
            if choix == "1":
                self.difficulte = "facile"
                break
            elif choix == "2":
                self.difficulte = "moyen"
                break
            elif choix == "3":
                self.difficulte = "difficile"
                break
            else:
                print("Choix invalide. Veuillez choisir 1, 2 ou 3.")
    def demarrer(self):
        """Lance le jeu avec les paramètres de difficulté"""
        print("\nBienvenue dans le Jeu Simon!")
        
        # Créer un Event pour signaler que la connexion est établie
        connexion_etablie = Event()
        
        @self.socket.event
        def connect():
            connexion_etablie.set()
        
        try:
            if not self.mode_test:
                print("Connexion au serveur...")
                self.socket.connect(
                    'http://192.168.5.5:8000',
                    transports=['websocket'],
                    wait=False
                )
                # Attendre la connexion avec un timeout
                if not connexion_etablie.wait(timeout=10):
                    raise Exception("Timeout de connexion")
                print("Connecté en mode NORMAL")
                
                # Choix de la difficulté avec le tapis en mode normal
                print("\nMode de sélection de la difficulté par le tapis activé")
                self.choisir_difficulte_avec_tapis()
                
            else:
                print("Démarrage en mode TEST")
                # En mode test, choix manuel
                self.choisir_difficulte_manuelle()

        except Exception as e:
            print(f"Erreur de connexion : {str(e)}")
            print("Passage en mode TEST")
            self.mode_test = True
            self.choisir_difficulte_manuelle()

        self.afficher_parametres_difficulte()
        time.sleep(2)  # Pause pour lire les paramètres
        
        # Démarrer le jeu après avoir choisi la difficulté
        if not self.mode_test:
            game_thread = Thread(target=self.demarrer_jeu, daemon=True)
            game_thread.start()
            self.socket.wait()  # Attendre les événements socket
        else:
            self.demarrer_jeu()

class EtatJeu:
    def __init__(self):
        self.sequence = []
        self.score = 0
        self.couleurs = Queue()
        self.peut_jouer = False
        self.position = 0
        self.pas_en_cours = Event()  # Event pour suivre les pas
        self.pas_en_cours.clear()
        self.derniere_couleur_ajoutee = None
        self.derniere_detection = 0

    def reinitialiser(self):
        """Remet à zéro l'état pour une nouvelle partie."""
        self.score = 0
        self.sequence = []
        self.preparer_tour()

    def preparer_tour(self):
        """Prépare le jeu pour un nouveau tour."""
        # Note: peut_jouer est maintenant géré via l'événement objects-update
        self.position = 0
        self.pas_en_cours.clear()
        self.derniere_couleur_ajoutee = None  # Réinitialise la dernière couleur

    def ajouter_couleur(self, couleur):
        """
        Ajoute une nouvelle couleur à la file avec gestion du délai
        """
        temps_actuel = time.time()
        # Ajouter un délai minimum entre les détections (par exemple 0.5 secondes)
        if temps_actuel - self.derniere_detection > 0.5:
            self.derniere_couleur_ajoutee = couleur
            self.couleurs.put(couleur)
            self.position += 1
            self.derniere_detection = temps_actuel

if __name__ == "__main__":
    try:
        jeu = JeuSimon(mode_test=False)
        # Le jeu démarrera automatiquement lors de la réception du message sur site/start
        while True:
            time.sleep(1)  # Maintenir le programme en vie
    except KeyboardInterrupt:
        jeu.stop()
        print("\nProgramme arrêté par l'utilisateur")