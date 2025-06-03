
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jeu Simon interactif avec SensFloor et communication MQTT.

Ce module implémente un jeu Simon qui peut fonctionner en mode normal avec un
SensFloor (tapis de détection de pas) ou en mode test avec saisie clavier.
Le jeu communique via MQTT pour la synchronisation des événements et la
gestion audio, et utilise Socket.IO pour la communication avec le SensFloor.

Le jeu supporte trois niveaux de difficulté :
- Facile : 100 secondes par couleur, ajoute 1 couleur par tour
- Moyen : 70 secondes par couleur, ajoute 1 couleur par tour  
- Difficile : 50 secondes par couleur, ajoute 2 couleurs par tour

Modules requis:
    - datetime: Gestion des timestamps
    - queue: Communication thread-safe
    - threading: Gestion des threads
    - random: Génération aléatoire des séquences
    - socketio: Communication avec le SensFloor
    - paho.mqtt.client: Communication MQTT
    - json: Sérialisation des messages
    - pygame: Gestion audio
    - msvcrt: Détection des touches (Windows)

Auteur: Jossua Nabec et Charlotte Conte
Version: 1.12
Date: 03/06/2025
"""

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
import platform

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    import msvcrt
else:
    import select
    import termios
    import tty
def input_with_timeout(prompt, timeout):
    """
    Fonction input compatible Windows et Linux avec timeout
    Retourne None si timeout expiré
    """
    print(prompt, end='', flush=True)
    if IS_WINDOWS:
        start_time = time.time()
        input_str = ""
        while True:
            if msvcrt.kbhit():
                char = msvcrt.getch()
                if char in [b'\r', b'\n']:
                    print()
                    return input_str
                elif char == b'\x08':  # backspace
                    input_str = input_str[:-1]
                    print('\b \b', end='', flush=True)
                else:
                    try:
                        char_decoded = char.decode('utf-8')
                        input_str += char_decoded
                        print(char_decoded, end='', flush=True)
                    except Exception:
                        pass
            if time.time() - start_time > timeout:
                print()
                return None
            time.sleep(0.01)
    else:
        # Linux (Raspberry Pi)
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            rlist, _, _ = select.select([fd], [], [], timeout)
            if rlist:
                input_str = ""
                while True:
                    char = sys.stdin.read(1)
                    if char in ['\r', '\n']:
                        print()
                        return input_str
                    elif char == '\x7f':  # backspace
                        input_str = input_str[:-1]
                        print('\b \b', end='', flush=True)
                    else:
                        input_str += char
                        print(char, end='', flush=True)
            else:
                print()
                return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return None
class Son:
    """
    Gestionnaire audio pour le jeu Simon.
    
    Cette classe gère le préchargement et la lecture des fichiers audio
    via pygame.mixer, avec support de la lecture asynchrone via une queue
    et gestion des différents niveaux de difficulté.
    """

    def __init__(self, broker="10.0.200.7", port=1883, topic="Tapis/sequence", mqtt_client=None):
        """
        Initialise le gestionnaire audio.

        Args:
            broker (str): Adresse IP du broker MQTT. Défaut: "10.0.200.7"
            port (int): Port du broker MQTT. Défaut: 1883
            topic (str): Topic MQTT principal. Défaut: "Tapis/sequence"
            mqtt_client: Instance du client MQTT existant ou None
        """
        # Initialiser pygame.mixer pour l'audio
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)        
        # Ajouter une queue pour les sons à jouer
        self.sound_queue = Queue()       
        # Configuration MQTT
        self.topic = topic
        self.difficulty_topic = "site/difficulte"  # Définir explicitement
        if mqtt_client:
            self.client = mqtt_client
        else:
            self.client = mqtt.Client()
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
        # Obtenir le chemin du dossier courant
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Chemin du dossier des sons
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
            self.client.loop_start()
        except Exception as e:
            print(f"Erreur de connexion au broker MQTT: {e}")
        # Démarrer le thread MQTT
        self.client.loop_start()       
        # Démarrer le thread de lecture des sons
        self.running = True
        self.sound_thread = Thread(target=self._sound_worker, daemon=True)
        self.sound_thread.start()

    def _sound_worker(self):
        """
        Thread worker pour jouer les sons de manière asynchrone.
        
        Boucle continue qui récupère les séquences de sons depuis la queue
        et les joue via _play_sounds().
        """
        while self.running:
            try:
                sequence = self.sound_queue.get(timeout=0.1)
                self._play_sounds(sequence)
            except Empty:
                continue
            except Exception as e:
                print(f"Erreur dans le worker de son: {e}")

    def _play_sounds(self, sequence):
        """
        Joue une séquence de sons avec timing adapté à la difficulté.

        Args:
            sequence (list): Liste des numéros de sons à jouer
        """
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
        """
        Ajoute une séquence de sons à la queue de lecture.

        Args:
            sequence (list): Séquence de numéros de sons à jouer
        """
        self.sound_queue.put(sequence)

    def on_message(self, client, userdata, msg):
        """
        Callback MQTT appelé lors de la réception d'un message.

        Args:
            client: Instance du client MQTT
            userdata: Données utilisateur associées au client
            msg: Message MQTT reçu
        """
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
        """
        Callback MQTT appelé lors de la connexion au broker.

        Args:
            client: Instance du client MQTT
            userdata: Données utilisateur associées au client
            flags: Dictionnaire des flags de connexion
            rc (int): Code de retour de connexion
        """
        if rc == 0:
            print(f"Connecté aux topics: {self.topic}, {self.difficulty_topic}")
            client.subscribe(self.topic)
            client.subscribe(self.difficulty_topic)
        else:
            print(f"Échec de connexion, code retour = {rc}")

    def stop(self):
        """
        Arrête proprement le gestionnaire audio.
        
        Ferme les threads, arrête pygame.mixer et déconnecte le client MQTT.
        """
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
    
    Gère la logique du jeu, la communication avec le SensFloor via Socket.IO,
    la communication MQTT pour l'audio et les événements, et les différents
    modes de jeu (normal avec tapis, test avec clavier).
    """

    def __init__(self, mode_test=False):
        """
        Initialise une nouvelle instance du jeu Simon.

        Args:
            mode_test (bool): Si True, active le mode test avec saisie clavier.
                             Si False, utilise le SensFloor. Défaut: False
        """
        self.difficulty_topic = "site/difficulte"
        self.difficulty_timeout = 30  # 30 secondes pour choisir la difficulté
        self.difficulty_received = False
        self.waiting_for_difficulty = False
        self.last_difficulty_time = time.time()
        self.difficulty_map = {
            0: "facile",
            1: "moyen", 
            2: "difficile"
        }
        self.dernier_pas = 0
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
        self.mqtt_broker = "10.0.200.7"
        self.mqtt_port = 1883
        self.mqtt_topic = "Tapis/sequence"
        self.led_status_topic = "LED/status"
        self.start_topic = "site/start"  # Topic pour démarrer le jeu
        self.game_started = False       
        # Configure le callback pour la réception des messages
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.subscribe([
            (self.start_topic, 0),
            (self.difficulty_topic, 0)
        ])  # Nouveau callback pour les abonnements
        self.mqtt_client.on_connect = self.on_connect
        # Initialize MQTT connection
        try:
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port)
            self.mqtt_client.loop_start()
        except Exception as e:
            print(f"Erreur de connexion MQTT: {e}")
        self.sound_manager = Son(mqtt_client=self.mqtt_client)
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

    def handle_difficulty_message(self, payload):
        """
        Traite les messages de difficulté reçus via MQTT.

        Args:
            payload (str): Message JSON contenant la difficulté au format {'dif': 0-2}
        """
        try:
            print(f"Reception difficulté: {payload}")
            data = json.loads(payload)
            
            # Vérifier si c'est un message de confirmation
            if "status" in data:
                print("Message de confirmation reçu, ignoré")
                return
                
            if not isinstance(data, dict) or 'dif' not in data:
                raise ValueError("Format attendu: {'dif': 0-2}")
                
            dif_value = data['dif']
            if isinstance(dif_value, str) and dif_value.isdigit():
                dif_value = int(dif_value)
                
            if not isinstance(dif_value, int) or dif_value not in [0, 1, 2]:
                raise ValueError("La valeur doit être 0, 1 ou 2")                
            self.difficulte = self.difficulty_map[dif_value]
            self.difficulty_received = True
            self.waiting_for_difficulty = False   
            print(f"Difficulté appliquée: {self.difficulte}")
            self.afficher_parametres_difficulte()            
            # Confirmation MQTT
            confirmation = {
                "status": "ok",
                "received_dif": dif_value,
                "applied_difficulty": self.difficulte,
                "timestamp": datetime.now().isoformat()
            }
            self.mqtt_client.publish(self.difficulty_topic, json.dumps(confirmation))           
        except Exception as e:
            error_msg = {
                "status": "error",
                "message": str(e),
                "expected_format": {"dif": "0-2"},
                "timestamp": datetime.now().isoformat()
            }
            self.mqtt_client.publish(self.difficulty_topic, json.dumps(error_msg))
            print(f"Erreur traitement difficulté: {e}")

    def afficher_parametres_difficulte(self):
        """
        Affiche les paramètres du niveau de difficulté actuellement sélectionné.
        """
        config = self.config_difficulte[self.difficulte]
        print("\nParamètres actuels :")
        print(f"- Temps pour reproduire chaque couleur : {config['temps_attente']} secondes")
        print(f"- Nouvelles couleurs par tour : {config['nouvelles_couleurs']}")
        print(f"- Temps entre chaque couleur : {config['temps_sequence']} secondes")
        print(f"- Délai entre les tours : {config['delai_entre_tours']} secondes")

    def on_connect(self, client, userdata, flags, rc):
        """
        Callback MQTT appelé lors de la connexion au broker.

        Args:
            client: Instance du client MQTT
            userdata: Données utilisateur associées au client
            flags: Dictionnaire des flags de connexion
            rc (int): Code de retour de connexion
        """
        if rc == 0:
            # S'abonner à tous les topics nécessaires
            topics = [
                (self.difficulty_topic, 0),
                (self.start_topic, 0),
                (self.mqtt_topic, 0)
            ]
            client.subscribe(topics)
            print(f"Abonné aux topics: {[topic for topic, qos in topics]}")
        else:
            print(f"Échec de connexion MQTT, code={rc}")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        """
        Callback MQTT appelé lors de l'abonnement réussi à un topic.

        Args:
            client: Instance du client MQTT
            userdata: Données utilisateur associées au client
            mid: Identifiant du message d'abonnement
            granted_qos (list): Liste des niveaux QoS accordés
        """
        print(f"Successfully subscribed to topics with QoS: {granted_qos}")

    def mode_switch_monitor(self):
        """
        Thread de surveillance pour le changement de mode et l'arrêt du jeu.
        
        Permet de basculer entre mode test/normal et de quitter proprement.
        """
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
        """
        Bascule entre le mode test (clavier) and mode normal (SensFloor).
        """
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

    def mode_test_simuler_pas(self):
        """
        Simule la saisie des pas en mode test avec gestion du temps et de la difficulté.

        Returns:
            bool: True si la séquence est complétée avec succès, False sinon
        """
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
        """
        Convertit une séquence de couleurs en séquence de chiffres.

        Args:
            sequence (list): Liste de noms de couleurs

        Returns:
            list: Liste des chiffres correspondants aux couleurs
        """
        return [self.couleur_vers_chiffre[couleur] for couleur in sequence]

    def on_mqtt_message(self, client, userdata, message):
        """
        Gestionnaire principal des messages MQTT reçus.

        Args:
            client: Instance du client MQTT
            userdata: Données utilisateur associées au client
            message: Message MQTT reçu
        """
        try:
            topic = message.topic
            payload = message.payload.decode()
            
            if topic == self.difficulty_topic:
                self.handle_difficulty_message(payload)
            elif topic == self.start_topic:
                if payload.lower() == "true":
                    if not self.game_started:
                        print("Démarrage d'une nouvelle partie...")
                        self.game_started = True
                        self.waiting_for_difficulty = True
                        self.last_difficulty_time = time.time()
                        # Réinitialiser l'état du jeu
                        self.etat.reinitialiser()
                        game_thread = Thread(target=self.demarrer, daemon=True)
                        game_thread.start()
                    else:
                        print("Une partie est déjà en cours")
                
        except Exception as e:
            print(f"Error processing MQTT message: {e}")

    def reset_game(self):
        """
        Réinitialise complètement l'état du jeu pour une nouvelle partie.
        """
        self.game_started = False
        self.waiting_for_difficulty = False
        self.etat.reinitialiser()

    def publier_sequence_mqtt(self, sequence, tmp, index, type_sequence="generated"):
        """
        Publie une séquence sur le topic MQTT après conversion en chiffres.

        Args:
            sequence (list): Séquence de couleurs à publier
            tmp (int): Type de message (1=couleur unique, 2=séquence complète, 3=erreur)
            index (int): Index de la couleur dans la séquence (pour tmp=1)
            type_sequence (str): Type de séquence pour le logging
        """
        try:
            if tmp == 3:
                error_message = {"couleur": [4], "pas": False}
                self.mqtt_client.publish(self.mqtt_topic, json.dumps(error_message))
                print(f"Error sequence published to MQTT: {error_message}")
                return
            sequence_chiffres = self.convertir_sequence_en_chiffres(sequence)
            if tmp == 2:
                message = {"couleur": sequence_chiffres,"pas": True}
                print(f"MQTT >>> [Tapis/sequence] Séquence complète : {json.dumps(message)}")
            elif tmp == 1:
                message = {"couleur": [self.couleur_vers_chiffre[couleur]],"pas": False}
                print(f"MQTT >>> [Tapis/sequence] Couleur unique : {json.dumps(message)}")
            self.mqtt_client.publish(self.mqtt_topic, json.dumps(message))
            print(f"Sequence published to MQTT: {message}")
        except Exception as e:
            error_message = {"couleur": [4],"pas": False}
            self.mqtt_client.publish(self.mqtt_topic, json.dumps(error_message))
            print(f"Failed to publish to MQTT: {e}")
            print(f"Sent error sequence: {error_message}")

    def montrer_sequence(self, temps_sequence):
        """
        Affiche et envoie la séquence complète avec le son de fin.

        Args:
            temps_sequence (float): Temps d'attente entre chaque couleur (non utilisé ici)
        """
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
        """
        Configure les événements de connexion socket pour la communication avec le SensFloor.
        
        Cette méthode définit les callbacks pour les événements socket.io :
        - connect : appelé lors de l'établissement de la connexion
        - disconnect : appelé lors de la perte de connexion
        - step : appelé lors de la détection d'un pas sur le tapis
        - objects-update : appelé lors de la mise à jour des objets détectés
        
        Note:
            Les callbacks sont définis comme des fonctions internes pour avoir accès
            aux attributs de l'instance via la fermeture (closure).
        """
        
        @self.socket.event
        def connect():
            """
            Callback appelé lors de l'établissement de la connexion socket.
            
            Configure le timeout de ping et affiche un message de confirmation.
            Le timeout est défini à 2 secondes pour maintenir une connexion active.
            """
            print("Connecté au serveur SensFloor")
            self.socket.eio.ping_timeout = 2000  # 2 seconds

        @self.socket.event
        def disconnect():
            """
            Callback appelé lors de la perte de connexion socket.
            
            En cas de déconnexion pendant une partie, force la reprise du jeu
            pour éviter un blocage de l'état de jeu.
            """
            print("Déconnecté du serveur")
            if not self.etat.peut_jouer:
                self.etat.peut_jouer = True
                print("Forçage de la reprise du jeu après déconnexion")

        @self.socket.on('step')
        def on_pas(x, y):
            """
            Callback appelé lors de la détection d'un pas sur le SensFloor.
            
            Args:
                x (float): Coordonnée X du pas détecté sur le tapis
                y (float): Coordonnée Y du pas détecté sur le tapis
                
            Note:
                Délègue le traitement à la méthode traiter_pas() de l'instance.
            """
            self.traiter_pas(x, y)
            
        @self.socket.on('objects-update')
        def on_objects_update(objects):
            """
            Callback appelé lors de la mise à jour des objets détectés sur le tapis.
            
            Args:
                objects (list): Liste des objets actuellement détectés sur le tapis
                
            Note:
                Active la détection des pas pour permettre une nouvelle séquence
                de jeu lorsque des objets sont détectés.
            """
            if isinstance(objects, list):
                self.etat.peut_jouer = True
                #print("Détection des pas activée pour nouvelle séquence")

    def creer_sequence(self, seq_precedente):
        """
        Crée une nouvelle séquence de couleurs basée sur la séquence précédente.
        
        Args:
            seq_precedente (list): Liste des couleurs de la séquence précédente.
                                 Peut être vide pour la première séquence.
        
        Returns:
            list: Nouvelle séquence avec une couleur supplémentaire ajoutée.
                 La nouvelle couleur est différente de la dernière de la séquence précédente.
        
        Note:
            Cette méthode ne publie plus la séquence via MQTT, cette responsabilité
            a été déplacée vers d'autres méthodes pour une meilleure séparation des préoccupations.
        """
        couleurs = ['vert', 'rouge', 'bleu', 'jaune']
        if seq_precedente:
            # Évite de répéter la dernière couleur
            couleurs = [c for c in couleurs if c != seq_precedente[-1]]
        nouvelle_sequence = seq_precedente + [random.choice(couleurs)]
        # On ne publie plus la séquence ici
        return nouvelle_sequence

    def afficher_sequence(self, sequence):
        """
        Affiche la séquence que le joueur doit reproduire avec les chiffres correspondants.
        
        Args:
            sequence (list): Liste des couleurs à afficher dans l'ordre.
                           Chaque couleur est représentée par son nom en français.
        
        Note:
            Affiche chaque couleur avec son numéro d'ordre et le chiffre correspondant
            utilisé pour la communication MQTT et la saisie en mode test.
        """
        print("\nSéquence à reproduire :")
        for i, couleur in enumerate(sequence, 1):
            chiffre = self.couleur_vers_chiffre[couleur]
            print(f"{i}. {couleur} ({chiffre})")
        print("\n")

    def detecter_couleur(self, x, y):
        """
        Convertit les coordonnées du pas en couleur correspondante sur le SensFloor.
        
        Le SensFloor est divisé en 4 zones de couleur selon un quadrillage 2x2 :
        - Zone supérieure gauche (0 ≤ x ≤ 0.5, 1 ≤ y ≤ 1.5) : vert
        - Zone inférieure gauche (0 ≤ x ≤ 0.5, y < 1 ou y > 1.5) : rouge  
        - Zone supérieure droite (0.5 < x ≤ 1, 1 ≤ y ≤ 1.5) : jaune
        - Zone inférieure droite (0.5 < x ≤ 1, y < 1 ou y > 1.5) : bleu
        
        Args:
            x (float): Coordonnée X normalisée (0.0 à 1.0) du pas sur le tapis
            y (float): Coordonnée Y normalisée (0.0 à 2.0) du pas sur le tapis
        
        Returns:
            str: Nom de la couleur correspondante ('vert', 'rouge', 'bleu', 'jaune')
                 ou 'inconnu' si les coordonnées sont hors des zones définies
        """
        if 0 <= x <= 0.5:
            return 'vert' if 1 <= y <= 1.5 else 'rouge'
        elif 0.5 < x <= 1:
            return 'jaune' if 1 <= y <= 1.5 else 'bleu'
        return 'inconnu'

    def reinitialiser_queue_couleurs(self):
        """
        Vide complètement la queue des couleurs détectées.
        
        Cette méthode supprime toutes les couleurs en attente dans la queue
        pour préparer une nouvelle séquence ou réinitialiser l'état du jeu.
        
        Note:
            Utilise une boucle pour vider la queue de manière thread-safe
            en récupérant tous les éléments jusqu'à ce qu'elle soit vide.
        """
        while not self.etat.couleurs.empty():
            self.etat.couleurs.get()

    def traiter_pas(self, x, y):
        """
        Traite un nouveau pas détecté sur le SensFloor avec gestion des doublons et du timing.
        
        Cette méthode convertit les coordonnées en couleur, applique un filtre temporel
        pour éviter les détections multiples rapides, et publie la couleur détectée via MQTT.
        
        Args:
            x (float): Coordonnée X du pas détecté (0.0 à 1.0)
            y (float): Coordonnée Y du pas détecté (0.0 à 2.0)
        
        Note:
            - Ignore les pas si le jeu n'est pas en état de réception (peut_jouer = False)
            - Applique un délai minimum de 0.5 seconde entre les détections
            - Ignore les couleurs identiques consécutives pour éviter les rebonds
            - Publie chaque couleur valide via MQTT sur le topic de séquence
        """
        if not self.etat.peut_jouer:
            return
        try:
            x, y = float(x), float(y)
            couleur = self.detecter_couleur(x, y)
            if couleur == 'inconnu':
                return
            temps_actuel = time.time()
            # Vérifier si le temps minimum est écoulé et si la couleur est différente de la dernière
            if  temps_actuel - self.dernier_pas > 0.5 and couleur != self.etat.derniere_couleur_detectee:
                print(f"Nouvelle couleur : {couleur}")
                self.etat.ajouter_couleur(couleur)
                self.dernier_pas = temps_actuel
                self.etat.derniere_couleur_detectee = couleur  # Sauvegarder la dernière couleur
                # Envoyer la couleur détectée en MQTT uniquement
                chiffre = self.couleur_vers_chiffre[couleur]
                message = {"couleur": [chiffre],"pas": False}
                self.mqtt_client.publish(self.mqtt_topic, json.dumps(message))
                print(f"MQTT >>> [Tapis/sequence] Détection pas : {json.dumps(message)}")
            else:
                # Si c'est la même couleur, ne rien faire
                if couleur == self.etat.derniere_couleur_detectee:
                    print(f"Même couleur que la précédente ({couleur}), ignorée")
        except Exception as e:
            print(f"Erreur : {str(e)}")

    def attendre_fin_pas(self, timeout=1.0):
        """
        Attend que le joueur ne soit plus sur une zone du tapis avec timeout.
        
        Cette méthode utilise un Event pour détecter si un nouveau pas est en cours
        et attend un court instant pour vérifier l'absence de mouvement.
        
        Args:
            timeout (float, optional): Temps d'attente maximum en secondes. Défaut: 1.0
        
        Returns:
            bool: True si aucun pas n'est détecté pendant la période d'attente,
                  False si un pas est détecté pendant l'attente
        
        Note:
            Utilisée pour s'assurer que le joueur a quitté une zone avant
            de considérer la prochaine détection comme valide.
        """
        self.etat.pas_en_cours.clear()
        # Attend un court instant pour voir si un nouveau pas est détecté
        is_stepping = self.etat.pas_en_cours.wait(timeout)
        return not is_stepping

    def envoyer_erreur_mqtt(self, type_erreur="sequence"):
        """
        Envoie un message d'erreur via MQTT pour signaler un problème de jeu.
        
        Le message d'erreur utilise le code couleur 4 qui correspond à un signal d'erreur
        dans le protocole de communication avec les LEDs et le système audio.
        
        Args:
            type_erreur (str, optional): Type d'erreur pour le logging local.
                                       Défaut: "sequence"
        
        Note:
            - Ajoute un délai d'1 seconde avant l'envoi pour éviter les conflits
            - Le code 4 déclenche généralement un son d'erreur côté récepteur
            - Le paramètre "pas" est mis à False pour indiquer une couleur simple
        """
        error_message = {
            "couleur": [4],  # 4 représente une erreur
            "pas": False
        }
        time.sleep(1)
        self.mqtt_client.publish(self.mqtt_topic, json.dumps(error_message))
        
        print(f"MQTT >>> Envoi signal d'erreur : {error_message}")

    def stop(self):
        """
        Arrête proprement le jeu en fermant toutes les connexions et threads.
        
        Cette méthode effectue un arrêt complet et sécurisé de tous les composants :
        - Arrêt du gestionnaire de sons
        - Déconnexion du client MQTT
        - Déconnexion du socket SensFloor
        - Marquage de l'arrêt pour tous les threads
        
        Note:
            Gère les exceptions pour chaque composant individuellement afin d'assurer
            un arrêt propre même en cas d'erreur sur l'un des éléments.
        """
        print("Arrêt du jeu demandé")
        self.game_started = False
        self.running = False
        
        if hasattr(self, 'sound_manager'):
            try:
                self.sound_manager.stop()
            except Exception as e:
                print(f"Erreur lors de l'arrêt du gestionnaire de sons : {e}")
        
        if hasattr(self, 'mqtt_client'):
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
                print("Déconnexion du broker MQTT effectuée")
            except Exception as e:
                print(f"Erreur lors de la déconnexion MQTT : {e}")
        
        if hasattr(self, 'socket') and self.socket.connected:
            try:
                self.socket.disconnect()
                print("Déconnexion du socket effectuée")
            except Exception as e:
                print(f"Erreur lors de la déconnexion du socket : {e}")
        
        print("Arrêt du jeu terminé")

    def lire_sequence_test(self, longueur_sequence, temps_total):
        """
        Gère la saisie de la séquence en mode test avec vérification du temps global.
        
        En mode test, le joueur saisit les couleurs au clavier avec un timeout global
        pour toute la séquence. La méthode vérifie chaque entrée et arrête immédiatement
        en cas d'erreur ou de dépassement de temps.
        
        Args:
            longueur_sequence (int): Nombre de couleurs à saisir dans la séquence
            temps_total (float): Temps total alloué pour saisir toute la séquence (en secondes)
        
        Returns:
            list or None: Liste des couleurs saisies si succès, None en cas d'échec
                         (timeout, erreur de couleur, ou abandon)
        
        Note:
            - Utilise msvcrt.kbhit() pour une saisie non-bloquante sur Windows
            - Publie chaque couleur saisie via MQTT pour feedback visuel/audio
            - Envoie des signaux d'erreur MQTT spécifiques selon le type d'échec
            - Met à jour l'affichage du temps restant en temps réel
        """
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
                    char = get_single_char()
                    if char and char in ['0', '1', '2', '3', 'q']:
                        choix = char
                        print(char)
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
        """
        Gère la lecture de la séquence en mode normal avec le tapis SensFloor.
        
        En mode normal, la méthode attend que le joueur marche sur les zones colorées
        du tapis dans l'ordre correct, avec un timeout global pour toute la séquence.
        
        Args:
            longueur_sequence (int): Nombre de couleurs attendues dans la séquence
            temps_total (float): Temps total alloué pour compléter la séquence (en secondes)
        
        Returns:
            list or None: Liste des couleurs détectées si succès, None en cas d'échec
                         (timeout, erreur de couleur, ou problème technique)
        
        Note:
            - Active la réception des pas via self.etat.peut_jouer
            - Surveille la queue des couleurs détectées par traiter_pas()
            - Vérifie chaque couleur reçue contre la séquence attendue
            - Affiche le temps restant en temps réel sur la console
            - Publie les couleurs détectées et les erreurs via MQTT
        """
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
        """
        Lit la séquence entrée par le joueur selon le mode de jeu.

        Cette méthode gère la lecture de la séquence de couleurs saisie par le joueur, soit via le clavier
        (mode test), soit via le tapis SensFloor (mode normal). Elle applique les règles de temps et de
        validation des couleurs, et publie les couleurs saisies ou détectées sur le topic MQTT.

        Args:
            longueur_sequence (int): Nombre de couleurs attendues dans la séquence.

        Returns:
            list or None: La liste des couleurs saisies/détectées si la séquence est correcte,
                          None en cas d'erreur, de timeout ou d'abandon.

        Note:
            - Le temps total autorisé dépend du niveau de difficulté.
            - En mode test, la saisie se fait au clavier avec gestion du temps global.
            - En mode normal, la détection se fait via le SensFloor avec gestion du temps global.
        """
        config = self.config_difficulte[self.difficulte]
        temps_total = config['temps_attente'] * longueur_sequence
        print(f"\nTemps disponible pour cette séquence : {temps_total} secondes")

        if self.mode_test:
            return self.lire_sequence_test(longueur_sequence, temps_total)
        else:
            return self.lire_sequence_tapis(longueur_sequence, temps_total)

    def changer_difficulte(self, nouvelle_difficulte):
        """
        Change le niveau de difficulté du jeu.

        Modifie le niveau de difficulté courant si la valeur donnée est valide et met à jour l'affichage
        des paramètres associés à la difficulté sélectionnée.

        Args:
            nouvelle_difficulte (str): 'facile', 'moyen' ou 'difficile'
        """
        if nouvelle_difficulte in self.config_difficulte:
            self.difficulte = nouvelle_difficulte
            print(f"\nNiveau de difficulté changé à : {nouvelle_difficulte}")
            self.afficher_parametres_difficulte()
        else:
            print("Niveau de difficulté invalide. Choisissez entre : facile, moyen, difficile")

    def demarrer_jeu(self):
        """
        Gère une partie avec les paramètres de difficulté courants.

        Cette méthode lance le jeu Simon et gère la progression des séquences, la saisie du joueur,
        le calcul du score, la gestion des échecs et la publication du score final via MQTT.

        Note:
            - Utilise la méthode montrer_sequence() pour afficher la séquence.
            - Gère la progression du score.
            - Réinitialise le jeu et publie le score final en cas de perte ou d'erreur.
        """
        try:
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
                    # Partie perdue
                    print("\nPartie perdue !")
                    # Envoyer le score final
                    score_message = {
                        "score": score,
                        "difficulte": self.difficulte,
                        "timestamp": datetime.now().isoformat()
                    }
                    self.mqtt_client.publish("Tapis/score", json.dumps(score_message))
                    print(f"MQTT >>> [Tapis/score] Score final envoyé : {json.dumps(score_message)}")
                    self.reset_game()
                    return

                if sequence_joueur == self.etat.sequence:
                    score += len(sequence_joueur)
                    print(f"\nBravo ! Score actuel : {score}")
                else:
                    # Partie perdue
                    print("\nPartie perdue !")
                    # Envoyer le score final
                    score_message = {
                        "score": score,
                        "difficulte": self.difficulte,
                        "timestamp": datetime.now().isoformat()
                    }
                    self.mqtt_client.publish("Tapis/score", json.dumps(score_message))
                    print(f"MQTT >>> [Tapis/score] Score final envoyé : {json.dumps(score_message)}")
                    self.reset_game()
                    return

        except Exception as e:
            print(f"Erreur dans le jeu : {e}")
            # Envoyer le score même en cas d'erreur
            if 'score' in locals():
                score_message = {
                    "score": score,
                    "difficulte": self.difficulte,
                    "timestamp": datetime.now().isoformat(),
                    "ended_with_error": True
                }
                self.mqtt_client.publish("Tapis/score", json.dumps(score_message))
                print(f"MQTT >>> [Tapis/score] Score final envoyé (erreur) : {json.dumps(score_message)}")
            self.reset_game()

    def choisir_difficulte_avec_tapis(self):
        """
        Permet de choisir la difficulté en utilisant le tapis.

        Affiche la notice et attend la détection d'une couleur sur le tapis SensFloor pour choisir
        la difficulté. Timeout automatique au bout de 30 secondes (mode facile par défaut).

        Returns:
            str: difficulté sélectionnée ("facile", "moyen", "difficile")
        """
        print("\nChoisissez la difficulté en marchant sur une couleur :")
        print("VERT   : Mode Facile")
        print("ROUGE  : Mode Moyen")
        print("BLEU   : Mode Difficile")

        self.etat.peut_jouer = True
        choix_fait = Event()
        self.difficulte = None

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
        """
        Permet de choisir la difficulté manuellement via le clavier.

        Affiche les options et demande une saisie valide à l'utilisateur.
        """
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
        """
        Lance le jeu avec gestion MQTT de la difficulté et le mode sélectionné.

        Selon le mode (normal/test), attend la sélection de la difficulté puis lance la partie.
        En mode normal, attend le message de sélection de difficulté via MQTT.
        """
        print("\nBienvenue dans le Jeu Simon!")

        try:
            if not self.mode_test:
                # Vérifier si nous sommes déjà connectés
                if not hasattr(self, 'socket') or not self.socket.connected:
                    print("Connexion au serveur...")
                    self.socket.connect(
                        'http://192.168.5.5:8000',
                        transports=['websocket'],
                        wait=True,
                        wait_timeout=10
                    )
                    print("Connecté en mode NORMAL")

                # Attente de la difficulté via MQTT
                if not self.difficulty_received:
                    print("\nEn attente de la difficulté via MQTT...")
                    start_time = time.time()

                    while not self.difficulty_received and time.time() - start_time < self.difficulty_timeout:
                        remaining = int(self.difficulty_timeout - (time.time() - start_time))
                        if remaining % 5 == 0:
                            self.send_difficulty_reminder()
                        time.sleep(1)

                    if not self.difficulty_received:
                        print("\nPas de difficulté reçue, utilisation du mode facile par défaut")
                        self.difficulte = "facile"

                # Démarrer le jeu
                print("\nDémarrage du jeu en mode NORMAL")
                # Réinitialiser l'état du jeu
                self.etat.reinitialiser()
                game_thread = Thread(target=self.demarrer_jeu, daemon=True)
                game_thread.start()
                if not self.socket.connected:
                    self.socket.wait()
            else:
                print("Démarrage en mode TEST")
                if not hasattr(self, 'difficulte'):
                    self.choisir_difficulte_manuelle()
                self.demarrer_jeu()
        except Exception as e:
            print(f"Erreur de connexion : {str(e)}")
            if "Already connected" not in str(e):  # Ignorer l'erreur de connexion déjà établie
                print("Passage en mode TEST")
                self.mode_test = True
                if not hasattr(self, 'difficulte'):
                    self.choisir_difficulte_manuelle()
                self.demarrer_jeu()

    def send_difficulty_reminder(self):
        """
        Envoie un rappel pour la sélection de la difficulté sur le topic MQTT.

        Utilisé toutes les 5 secondes si la difficulté n'a pas encore été reçue.
        """
        reminder = {
            "type": "reminder",
            "message": "En attente de la difficulté",
            "format": {
                "dif": {
                    "type": "integer",
                    "values": {
                        "0": "facile",
                        "1": "moyen",
                        "2": "difficile"
                    }
                }
            },
            "example": {"dif": 1},
            "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.mqtt_client.publish(self.mqtt_topic, json.dumps(reminder))

class EtatJeu:
    """
    Classe pour gérer l'état du jeu Simon.
    """

    def __init__(self):
        """
        Initialise l'état du jeu.
        """
        self.sequence = []
        self.score = 0
        self.couleurs = Queue()
        self.peut_jouer = False
        self.position = 0
        self.pas_en_cours = Event()  # Event pour suivre les pas
        self.pas_en_cours.clear()
        self.derniere_couleur_ajoutee = None
        self.derniere_detection = 0
        self.derniere_couleur_detectee = None

    def reinitialiser(self):
        """
        Remet à zéro l'état pour une nouvelle partie.
        """
        self.score = 0
        self.sequence = []
        self.derniere_couleur_detectee = None  # Réinitialiser la dernière couleur détectée
        self.preparer_tour()

    def preparer_tour(self):
        """
        Prépare le jeu pour un nouveau tour.
        """
        self.position = 0
        self.pas_en_cours.clear()
        self.derniere_couleur_ajoutee = None  # Réinitialise la dernière couleur

    def ajouter_couleur(self, couleur):
        """
        Ajoute une nouvelle couleur à la file avec gestion du délai.

        Args:
            couleur (str): Nom de la couleur à ajouter.
        """
        temps_actuel = time.time()
        # Ajouter un délai minimum entre les détections (par exemple 0.5 secondes)
        if temps_actuel - self.derniere_detection > 0.5:
            self.derniere_couleur_ajoutee = couleur
            self.couleurs.put(couleur)
            self.position += 1
            self.derniere_detection = temps_actuel

if __name__ == "__main__":
    jeu = None
    try:
        jeu = JeuSimon(mode_test=False)
        print("Jeu Simon démarré, en attente des messages MQTT...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nArrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        if jeu:
            jeu.stop()
            print("Jeu arrêté proprement")