from datetime import datetime
from queue import Queue, Empty 
from threading import Event, Thread
import logging
import random
import socketio
import paho.mqtt.client as mqtt
import json
import sys
import time

class JeuSimon:
    """
    Classe principale du jeu Simon.
    Gère la logique du jeu et la communication avec le SensFloor.
    """

    def __init__(self, mode_test=False):
        # Configuration du fichier de log pour suivre les événements
        logging.basicConfig(
            filename='journal.txt',
            level=logging.INFO,
            format='%(asctime)s - %(message)s'
        )
        self.difficulte = "facile"
        
        self.config_difficulte = {
            "facile": {
                "temps_attente": 10.0,     # 20 secondes par couleur (augmenté)
                "nouvelles_couleurs": 1,    # Ajoute 1 couleur par tour
                "temps_sequence": 0.0,      # Pas de délai entre les couleurs
                "delai_entre_tours": 1.0    # Pas de délai entre les tours
            },
            "moyen": {
                "temps_attente": 7.0,      # 15 secondes par couleur (augmenté)
                "nouvelles_couleurs": 1,    # Ajoute 1 couleur par tour
                "temps_sequence": 0.0,      # Pas de délai entre les couleurs
                "delai_entre_tours": 1.0    # Pas de délai entre les tours
            },
            "difficile": {
                "temps_attente": 5.0,      # 10 secondes par couleur (augmenté)
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
        self.mqtt_broker = "192.168.1.103"
        self.mqtt_port = 1883
        self.mqtt_topic = "Tapis/sequence"
        self.led_status_topic = "LED/status"
        
        # Configure le callback pour la réception des messages
        self.mqtt_client.on_message = self.on_mqtt_message

        # Initialize MQTT connection
        try:
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port)
            self.mqtt_client.subscribe(self.led_status_topic)
            self.mqtt_client.loop_start()
            print("Connected to MQTT broker")
            print(f"Subscribed to topic: {self.led_status_topic}")
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")

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
    def afficher_parametres_difficulte(self):
        """Affiche les paramètres du niveau de difficulté actuel"""
        config = self.config_difficulte[self.difficulte]
        print("\nParamètres actuels :")
        print(f"- Temps pour reproduire chaque couleur : {config['temps_attente']} secondes")
        print(f"- Nouvelles couleurs par tour : {config['nouvelles_couleurs']}")
        print(f"- Temps entre chaque couleur : {config['temps_sequence']} secondes")
        print(f"- Délai entre les tours : {config['delai_entre_tours']} secondes")

    def mode_switch_monitor(self):
        """Monitor for mode switch commands"""
        while self.running:
            try:
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
            
            if topic == self.led_status_topic:
                #print(f"Received LED status: {payload}")
                # Vous pouvez traiter le message ici selon vos besoins
                try:
                    led_status = json.loads(payload)
                    #print(f"LED status decoded: {led_status}")
                    # Ajoutez ici le traitement spécifique pour le status LED
                except json.JSONDecodeError as e:
                    print(f"Error decoding LED status JSON: {e}")
            
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
        """Montre la séquence de couleurs"""
        print("\nAttention ! Voici la séquence :")
        for i, couleur in enumerate(self.etat.sequence, 1):
            message = {
                "couleur": [self.couleur_vers_chiffre[couleur]],
                "pas": False
            }
            #self.mqtt_client.publish(self.mqtt_topic, json.dumps(message))
            #print(f"MQTT >>> [Tapis/sequence] Affichage couleur : {json.dumps(message)}")
            print(f"{i}. {couleur} ({self.couleur_vers_chiffre[couleur]})")
            time.sleep(1) 

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
                logging.info("Détection des pas activée pour nouvelle séquence")
    def creer_sequence(self, seq_precedente):
        """Crée une nouvelle séquence de couleurs et la publie via MQTT."""
        couleurs = ['vert', 'rouge', 'bleu', 'jaune']
        if seq_precedente:
            # Évite de répéter la dernière couleur
            couleurs = [c for c in couleurs if c != seq_precedente[-1]]
        nouvelle_sequence = seq_precedente + [random.choice(couleurs)]
        self.publier_sequence_mqtt(nouvelle_sequence,2,0)
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
            
            # Mettre à jour la dernière couleur seulement après l'avoir ajoutée
            derniere_couleur = self.etat.derniere_couleur_ajoutee
            if couleur != derniere_couleur:
                print(f"Nouvelle couleur : {couleur}")
                self.etat.ajouter_couleur(couleur)
                self.etat.derniere_couleur_ajoutee = couleur
                
                # Envoyer la couleur détectée en MQTT
                message = {
                    "couleur": [self.couleur_vers_chiffre[couleur]],
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
    def lire_sequence_tapis(self, longueur_sequence, temps_total):
        """Gère la lecture de la séquence avec le tapis"""
        sequence_joueur = []
        sequence_start_time = time.time()
        
        # Vider la queue avant de commencer
        self.reinitialiser_queue_couleurs()
        self.etat.peut_jouer = True
        
        # Attendre un court instant pour s'assurer que le système est prêt
        time.sleep(0.2)
        
        while len(sequence_joueur) < longueur_sequence:
            # Vérifier le temps total écoulé
            temps_ecoule = time.time() - sequence_start_time
            temps_restant = temps_total - temps_ecoule
            
            if temps_restant <= 0:
                self.envoyer_erreur_mqtt("timeout")
                print(f"\nTemps écoulé ! Vous avez dépassé {temps_total} secondes.")
                return None
                
            # Afficher le temps restant périodiquement
            print(f"\rTemps restant : {temps_restant:.1f} secondes", end='', flush=True)
            
            # Attendre une nouvelle couleur de la queue
            try:
                couleur = self.etat.couleurs.get(timeout=0.5)
                if couleur:  # Vérifier que la couleur n'est pas None
                    sequence_joueur.append(couleur)
                    print(f"\nCouleur {len(sequence_joueur)}: {couleur} détectée")
                    
                    # Vérifier si la couleur est correcte
                    position = len(sequence_joueur) - 1
                    if couleur != self.etat.sequence[position]:
                        self.envoyer_erreur_mqtt("wrong_color")
                        print(f"\nErreur ! Couleur attendue : {self.etat.sequence[position]}")
                        print(f"Couleur reçue : {couleur}")
                        return None
                    
            except Empty:
                continue
                
        return sequence_joueur
    def lire_sequence_test(self, longueur_sequence, temps_total):
        """Gestion du mode test"""
        sequence_joueur = []
        sequence_start_time = time.time()
        
        for position in range(longueur_sequence):
            # Vérifier le temps total écoulé
            temps_ecoule = time.time() - sequence_start_time
            temps_restant = temps_total - temps_ecoule
            
            if temps_restant <= 0:
                self.envoyer_erreur_mqtt("timeout")
                print(f"\nTemps écoulé ! Vous avez dépassé {temps_total} secondes.")
                return None
                
            print(f"\nEntrez la couleur {position + 1}/{longueur_sequence}")
            print(f"Temps restant : {temps_restant:.1f} secondes")
            print("(0:vert, 1:rouge, 2:bleu, 3:jaune, q:quit)")
            print("> ", end='', flush=True)
            
            choix = input().lower()
            
            if choix == 'q':
                self.envoyer_erreur_mqtt("abandon")
                print("\nPartie abandonnée.")
                return None
                
            if choix not in ['0', '1', '2', '3']:
                self.envoyer_erreur_mqtt("invalid_input")
                print("Entrée invalide. Séquence annulée.")
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

    def lire_sequence_normal(self, longueur_sequence, config, sequence_start_time):
        """Gestion du mode normal avec le tapis"""
        sequence_joueur = []
        self.etat.peut_jouer = True
        position = 0
        
        def verifier_temps():
            current_time = time.time()
            return (current_time - sequence_start_time) > config['temps_attente']
        
        while position < longueur_sequence:
            if verifier_temps():
                self.envoyer_erreur_mqtt("timeout")
                print(f"\nTemps total écoulé ! Vous avez dépassé {config['temps_attente']} secondes.")
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
            
            # Envoyer la séquence
            sequence_message = {
                "couleur": [self.couleur_vers_chiffre[c] for c in self.etat.sequence],
                "pas": True
            }
            self.mqtt_client.publish(self.mqtt_topic, json.dumps(sequence_message))
            print(f"MQTT >>> [Tapis/sequence] Nouvelle séquence : {json.dumps(sequence_message)}")
            
            print("\nNouvelle séquence :")
            self.montrer_sequence(config['temps_sequence'])
            time.sleep(config['delai_entre_tours'])
            
            # Lire la séquence du joueur
            sequence_joueur = self.lire_sequence_joueur(len(self.etat.sequence))
            if sequence_joueur is None:
                break
                
            if sequence_joueur == self.etat.sequence:
                score += len(sequence_joueur)
                print(f"\nBravo ! Score actuel : {score}")
            else:
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
        
        except Exception as e:
            print(f"Erreur de connexion : {str(e)}")
            print("Passage en mode TEST")
            self.mode_test = True
            # En cas d'erreur, choix manuel
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
        self.derniere_couleur_ajoutee = None  # Pour empêcher les doublons

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
        Ajoute une nouvelle couleur à la file.
        Ne prend pas en compte les couleurs identiques consécutives.
        """
        self.derniere_couleur_ajoutee = couleur
        self.couleurs.put(couleur)
        self.position += 1


if __name__ == "__main__":
    jeu = JeuSimon(mode_test=False)
    jeu.demarrer()