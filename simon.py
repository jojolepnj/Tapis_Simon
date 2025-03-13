from datetime import datetime
from queue import Queue
from threading import Event
import logging
import random
import socketio

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

    def _config_socket(self):
        """Configure les événements de connexion socket."""
        
        @self.socket.event
        def connect():
            """Appelé quand la connexion est établie."""
            print("Connecté au serveur SensFloor")
            self.demarrer_jeu()

        @self.socket.event
        def disconnect():
            """Appelé quand la connexion est perdue."""
            print("Déconnecté du serveur")

        @self.socket.on('step')
        def on_pas(x, y):
            """Appelé quand un pas est détecté sur le SensFloor."""
            self.traiter_pas(x, y)

    def creer_sequence(self, seq_precedente):
        """
        Crée une nouvelle séquence de couleurs.
        Ajoute une couleur aléatoire à la séquence précédente.
        """
        couleurs = ['rouge', 'vert', 'bleu', 'jaune']
        if seq_precedente:
            # Évite de répéter la dernière couleur
            couleurs = [c for c in couleurs if c != seq_precedente[-1]]
        return seq_precedente + [random.choice(couleurs)]

    def afficher_sequence(self, sequence):
        """Affiche la séquence que le joueur doit reproduire."""
        print("\nSéquence à reproduire :")
        for i, couleur in enumerate(sequence, 1):
            print(f"{i}. {couleur}")
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
            return

        try:
            x, y = float(x), float(y)
            print(f"Pas détecté en : ({x}, {y})")
            
            # Active la détection de la prochaine couleur
            if not self.etat.pret:
                self.etat.pret = True
                print("Prêt pour la prochaine couleur")
            
            # Détecte et traite la couleur
            couleur = self.detecter_couleur(x, y)
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
        """
        Attend et enregistre la séquence de couleurs du joueur.
        Retourne la liste des couleurs détectées.
        """
        sequence = []
        self.etat.preparer_tour()
        
        print("Reproduisez la séquence...")
        print(f"Nombre de couleurs à reproduire : {taille}")
        
        while len(sequence) < taille:
            try:
                # Attend la prochaine couleur avec un timeout de 60 secondes
                couleur = self.etat.couleurs.get(timeout=60.0)
                sequence.append(couleur)
                print(f"Couleur {len(sequence)}/{taille} : {couleur}")
                
                # Attend que le joueur ne soit plus sur une zone
                while not self.attendre_fin_pas():
                    pass
                
            except Exception as e:
                print("Temps écoulé!")
                break
        
        self.etat.peut_jouer = False
        return sequence

    def demarrer_jeu(self):
        """Boucle principale du jeu."""
        self.etat.reinitialiser()
        
        while True:
            # Crée et affiche une nouvelle séquence
            self.etat.sequence = self.creer_sequence(self.etat.sequence)
            self.afficher_sequence(self.etat.sequence)
            
            # Attend la réponse du joueur
            sequence_joueur = self.lire_sequence_joueur(len(self.etat.sequence))
            
            if not sequence_joueur:
                print("Partie terminée - Temps écoulé!")
                break
                
            # Vérifie si la séquence est correcte
            if sequence_joueur != self.etat.sequence:
                print(f"\nIncorrect!")
                print(f"Séquence attendue : {' '.join(self.etat.sequence)}")
                print(f"Votre séquence   : {' '.join(sequence_joueur)}")
                print(f"\nScore final : {self.etat.score}")
                break
                
            self.etat.score += 1
            print(f"\nBravo! Score : {self.etat.score}")

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
        self.derniere = None
        self.position = 0
        self.pret = False
        self.pas_en_cours = Event()  # Ajout d'un Event pour suivre les pas
        self.pas_en_cours.clear()    # Initialisation à False

    def reinitialiser(self):
        """Remet à zéro l'état pour une nouvelle partie."""
        self.score = 0
        self.sequence = []
        self.preparer_tour()

    def preparer_tour(self):
        """Prépare le jeu pour un nouveau tour."""
        self.peut_jouer = True
        self.derniere = None
        self.position = 0
        self.pret = False
        self.pas_en_cours.clear()

    def ajouter_couleur(self, couleur):
        """
        Ajoute une nouvelle couleur détectée à la file.
        Ne prend en compte que les changements de couleur.
        """
        if couleur == 'inconnu':
            return

        self.pas_en_cours.set()  # Indique qu'un pas est en cours
        
        if couleur != self.derniere and self.pret:
            print(f"Nouvelle couleur : {couleur}")
            self.derniere = couleur
            self.couleurs.put(couleur)
            self.position += 1
            self.pret = False


if __name__ == "__main__":
    jeu = JeuSimon()
    jeu.demarrer()