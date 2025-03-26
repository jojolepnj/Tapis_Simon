from datetime import datetime
from queue import Queue
from threading import Event, Thread
import logging
import random
import socketio
import paho.mqtt.client as mqtt
import json
import sys

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
        """Simulate steps in test mode via terminal input"""
        print("\nTest Mode - Séquence à reproduire :")
        for i, couleur in enumerate(self.etat.sequence, 1):
            print(f"{i}. {couleur} ({self.couleur_vers_chiffre[couleur]})")
        
        self.etat.preparer_tour()
        derniere_couleur = None
        sequence_joueur = []
        
        while self.etat.position < len(self.etat.sequence):
            try:
                print(f"\nEntrez la couleur {self.etat.position + 1}/{len(self.etat.sequence)}")
                print("(0:vert, 1:rouge, 2:bleu, 3:jaune, q:quit)")
                choix = input("> ").lower()
                
                if choix == 'q':
                    raise Exception("Test mode terminated")
                
                if choix in ['0', '1', '2', '3']:
                    couleur = self.chiffre_vers_couleur[int(choix)]
                    
                    if couleur == derniere_couleur:
                        print("Même couleur que la précédente, ignorée")
                        continue
                        
                    derniere_couleur = couleur
                    sequence_joueur.append(couleur)
                    self.etat.ajouter_couleur(couleur)
                    print(f"Couleur ajoutée : {couleur}")
                    
                    # Publier vers MQTT avec pas=false pour une couleur individuelle
                    message = {
                        "couleur": self.couleur_vers_chiffre[couleur],
                        "pas": False
                    }
                    self.mqtt_client.publish(self.mqtt_topic, json.dumps(message))
                    print(f"Published to MQTT: {message}")
                    
                    # Vérifier si la couleur est correcte
                    if couleur != self.etat.sequence[self.etat.position - 1]:
                        print(f"\nErreur! Couleur attendue : {self.etat.sequence[self.etat.position - 1]}")
                        return False  # Sortir immédiatement en cas d'erreur
                        
                else:
                    print("Entrée invalide. Utilisez 0-3 ou q pour quitter")
                    
            except Exception as e:
                print(f"Erreur mode test : {e}")
                return False
        
        # Publier la séquence complète à la fin si tout est correct
        if sequence_joueur == self.etat.sequence:
            message = {
                "couleur": [self.couleur_vers_chiffre[c] for c in sequence_joueur],
                "pas": True
            }
            self.mqtt_client.publish(self.mqtt_topic, json.dumps(message))
            print(f"Final sequence published to MQTT: {message}")
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
                print(f"Received LED status: {payload}")
                # Vous pouvez traiter le message ici selon vos besoins
                try:
                    led_status = json.loads(payload)
                    print(f"LED status decoded: {led_status}")
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
            elif tmp == 1:  # Single color case
                message = {
                    "couleur": sequence_chiffres[0],  # Toujours prendre le premier élément car on envoie une seule couleur
                    "pas": False
                }
            
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

    def _config_socket(self):
        """Configure les événements de connexion socket."""
        
        @self.socket.event
        def connect():
            """Appelé quand la connexion est établie."""
            print("Connecté au serveur SensFloor")
            # Configure timeout for faster detection of connection issues
            self.socket.eio.ping_timeout = 2000  # 2 seconds
            self.demarrer_jeu()

        @self.socket.event
        def disconnect():
            """Appelé quand la connexion est perdue."""
            print("Déconnecté du serveur")
            # Force peut_jouer to True if we've been waiting too long
            if not self.etat.peut_jouer:
                self.etat.peut_jouer = True
                print("Forçage de la reprise du jeu après déconnexion")

        @self.socket.on('step')
        def on_pas(x, y):
            """Appelé quand un pas est détecté sur le SensFloor."""
            self.traiter_pas(x, y)
            
        @self.socket.on('objects-update')
        def on_objects_update(objects):
            """
            Appelé quand une mise à jour des objets est reçue.
            Si la liste est vide, active la détection des pas pour la prochaine séquence.
            """
            if isinstance(objects, list):  # Remove len check to process all updates
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

    def traiter_pas(self, x, y):
        """Traite un nouveau pas détecté sur le SensFloor."""
        if not self.etat.peut_jouer:
            print("Détection des pas désactivée, en attente de l'événement objects-update")
            return

        try:
            x, y = float(x), float(y)
            print(f"Pas détecté en : ({x}, {y})")
            
            # Détecte la couleur
            couleur = self.detecter_couleur(x, y)
            if couleur == 'inconnu':
                return
                
            print(f"Couleur détectée : {couleur}")
            
            # Ne traite la couleur que si elle est différente de la dernière couleur ajoutée
            if couleur != self.etat.derniere_couleur_ajoutee:
                print(f"Nouvelle couleur : {couleur}")
                self.etat.ajouter_couleur(couleur)
                    
        except Exception as e:
            print(f"Erreur : {str(e)}")

        # Réinitialise le timer à chaque pas
        self.etat.pas_en_cours.set()

    def attendre_fin_pas(self, timeout=1.0):
        """Attend que le joueur ne soit plus sur une zone."""
        self.etat.pas_en_cours.clear()
        # Attend un court instant pour voir si un nouveau pas est détecté
        is_stepping = self.etat.pas_en_cours.wait(timeout)
        return not is_stepping

    def lire_sequence_joueur(self, taille):
        """Lit la séquence du joueur."""
        if self.mode_test:
            # Mode test via terminal
            sequence = []
            if self.mode_test_simuler_pas():
                while not self.etat.couleurs.empty():
                    sequence.append(self.etat.couleurs.get())
            else:
                # En cas d'erreur, on termine la partie
                message = {
                    "couleur": [4],
                    "pas": False
                }
                self.mqtt_client.publish(self.mqtt_topic, json.dumps(message))
                print("\nPartie terminée - Erreur dans la séquence!")
                print(f"Séquence attendue : {' '.join(self.etat.sequence)}")
                sequence = []  # Retourne une séquence vide pour indiquer l'erreur
                
            return sequence

        # Code original pour le mode normal
        sequence = []
        self.etat.preparer_tour()
        
        print("Reproduisez la séquence...")
        print(f"Nombre de couleurs à reproduire : {taille}")
        
        while len(sequence) < taille:
            try:
                couleur = self.etat.couleurs.get(timeout=60.0)
                sequence.append(couleur)
                print(f"Couleur {len(sequence)}/{taille} : {couleur}")
                
                # Publie la séquence partielle du joueur
                message = {
                    "couleur": self.couleur_vers_chiffre[couleur],
                    "pas": False
                }
                self.mqtt_client.publish(self.mqtt_topic, json.dumps(message))
                
                if couleur != self.etat.sequence[len(sequence)-1]:
                    print(f"\nErreur! Couleur attendue : {self.etat.sequence[len(sequence)-1]}")
                    print(f"Couleur reçue : {couleur}")
                    # Envoyer le message d'erreur
                    message = {
                        "couleur": [4],
                        "pas": False
                    }
                    self.mqtt_client.publish(self.mqtt_topic, json.dumps(message))
                    return []  # Retourne une séquence vide pour indiquer l'erreur
                
                while not self.attendre_fin_pas():
                    pass
                
            except Exception as e:
                print("Temps écoulé!")
                break
            
        self.etat.peut_jouer = False
        print("Séquence terminée, détection des pas désactivée")
        logging.info("Détection des pas désactivée après séquence")
        return sequence
    
    def demarrer_jeu(self):
        """Boucle principale du jeu."""
        self.etat.reinitialiser()
        
        while True:
            try:
                # Crée et affiche une nouvelle séquence
                self.etat.sequence = self.creer_sequence(self.etat.sequence)
                self.afficher_sequence(self.etat.sequence)
                
                if self.mode_test:
                    # En mode test, active immédiatement la séquence
                    self.etat.peut_jouer = True
                else:
                    # Désactive la détection des pas jusqu'à l'événement objects-update
                    self.etat.peut_jouer = False
                    print("En attente de l'événement objects-update pour activer la prochaine séquence...")
                    logging.info("En attente de l'événement objects-update")
                
                # Attend la réponse du joueur
                sequence_joueur = self.lire_sequence_joueur(len(self.etat.sequence))
                
                if not sequence_joueur:
                    print("Partie terminée - Temps écoulé!")
                    return  # Sortie propre du jeu
                    
                # Vérifie si la séquence est complète et correcte
                if len(sequence_joueur) < len(self.etat.sequence):
                    if not self.mode_test:
                        error_sequence = {'sequence': [4]}
                        self.mqtt_client.publish(self.mqtt_topic, json.dumps(error_sequence))
                    print("\nPartie terminée!")
                    print(f"Séquence attendue : {' '.join(self.etat.sequence)}")
                    print(f"Votre séquence   : {' '.join(sequence_joueur)} ❌")
                    print(f"\nScore final : {self.etat.score}")
                    return  # Sortie propre du jeu
                    
                self.etat.score += 1
                print(f"\nBravo! Score : {self.etat.score}")

            except Exception as e:
                print(f"Erreur dans la boucle de jeu: {str(e)}")
                logging.error(f"Erreur dans la boucle de jeu: {str(e)}")
                if not self.mode_test:
                    error_sequence = {'sequence': [4]}
                    self.mqtt_client.publish(self.mqtt_topic, json.dumps(error_sequence))
                return  # Sortie propre en cas d'erreur


    def demarrer(self):
        """Launch the game, falling back to test mode if server connection fails"""
        try:
            if not self.mode_test:
                print("Connecting to server...")
                self.socket.connect(
                    'http://192.168.5.5:8000',
                    transports=['websocket'],
                    wait=True,
                    wait_timeout=10
                )
                print("Connected in NORMAL mode")
                self.socket.wait()
            else:
                print("Starting in TEST mode")
                self.demarrer_jeu()
                
        except Exception as e:
            print(f"Connection error: {str(e)}")
            print("Falling back to TEST mode")
            self.mode_test = True
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
    # Start in normal mode first, will fall back to test if connection fails
    jeu = JeuSimon(mode_test=False)
    jeu.demarrer()