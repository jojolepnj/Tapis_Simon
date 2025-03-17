from datetime import datetime
from queue import Queue
from threading import Event
import logging
import random
import socketio
import paho.mqtt.client as mqtt
import json

class JeuSimon:
    """
    Classe principale du jeu Simon.
    Gère la logique du jeu et la communication avec le SensFloor.
    """

    def __init__(self):
        # Configuration du fichier de log pour suivre les événements
        logging.basicConfig(
            filename='journal.txt',
            level=logging.INFO,
            format='%(asctime)s - %(message)s'
        )
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
        self.mqtt_broker = "10.0.200.6"
        self.mqtt_port = 1883
        self.mqtt_topic = "Tapis/sequence"
        self.led_status_topic = "LED/status"  # Ajout du nouveau topic
        
        # Configure le callback pour la réception des messages
        self.mqtt_client.on_message = self.on_mqtt_message

        # Initialize MQTT connection
        try:
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port)
            # S'abonne au topic LED/status
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
                    "sequence": [4]  # Always send [4] for errors
                }
                self.mqtt_client.publish(self.mqtt_topic, json.dumps(error_message))
                print(f"Error sequence published to MQTT: {error_message}")
                return

            sequence_chiffres = self.convertir_sequence_en_chiffres(sequence)
            if tmp == 2:  # Full sequence case
                message = {
                    "sequence": sequence_chiffres
                }
            elif tmp == 1:  # Single color case
                message = {
                    "sequence": sequence_chiffres[index-1]
                }
            
            self.mqtt_client.publish(self.mqtt_topic, json.dumps(message))
            print(f"Sequence published to MQTT: {message}")
            
        except Exception as e:
            error_message = {
                "sequence": [4]  # Send [4] on any error
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
            return 'vert' if 1 <= y <= 1.5 else 'rouge'
        elif 0.5 < x <= 1:
            return 'jaune' if 1 <= y <= 1.5 else 'bleu'
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
        """Lit la séquence du joueur et la publie via MQTT."""
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
                self.publier_sequence_mqtt(sequence,1,len(sequence), "player")
                
                if couleur != self.etat.sequence[len(sequence)-1]:
                    print(f"\nErreur! Couleur attendue : {self.etat.sequence[len(sequence)-1]}")
                    print(f"Couleur reçue : {couleur}")
                    return sequence
                
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
                
                # Désactive la détection des pas jusqu'à l'événement objects-update
                self.etat.peut_jouer = False
                print("En attente de l'événement objects-update pour activer la prochaine séquence...")
                logging.info("En attente de l'événement objects-update")
                
                # Add timeout for waiting for objects-update
                wait_start_time = datetime.now()
                max_wait_time = 5  # Maximum wait time in seconds
                
                while not self.etat.peut_jouer:
                    current_time = datetime.now()
                    elapsed_time = (current_time - wait_start_time).total_seconds()
                    
                    if elapsed_time > max_wait_time:
                        print("Délai d'attente dépassé pour objects-update, reprise du jeu...")
                        self.etat.peut_jouer = True
                        break
                    
                    # Attend avec un timeout court pour rester réactif
                    self.etat.pas_en_cours.wait(0.2)
                
                # Si on a dépassé le timeout, on passe au tour suivant
                if elapsed_time > max_wait_time:
                    continue
                
                # Attend la réponse du joueur
                sequence_joueur = self.lire_sequence_joueur(len(self.etat.sequence))
                
                if not sequence_joueur:
                    print("Partie terminée - Temps écoulé!")
                    return  # Sortie propre du jeu
                    
                # Vérifie si la séquence est complète et correcte
                if len(sequence_joueur) < len(self.etat.sequence):
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
                error_sequence = {'sequence': [4]}
                self.mqtt_client.publish(self.mqtt_topic, json.dumps(error_sequence))
                return  # Sortie propre en cas d'erreur


    def demarrer(self):
        """Lance le jeu en se connectant au serveur."""
        try:
            print("Connexion au serveur...")
            self.socket.connect(
                'http://192.168.5.5:8000',
                transports=['websocket'],
                wait=True,
                wait_timeout=10
            )
            self.socket.wait()
        except Exception as e:
            print(f"Erreur de connexion : {str(e)}")

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
    jeu = JeuSimon()
    jeu.demarrer()