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
            
        @self.socket.on('objects-update')
        def on_objects_update(objects):
            """
            Appelé quand une mise à jour des objets est reçue.
            Si la liste est vide, active la détection des pas pour la prochaine séquence.
            """
            if isinstance(objects, list) and len(objects) == 0:
                #print("Liste d'objets vide reçue, activation de la détection des pas")
                self.etat.peut_jouer = True
                logging.info("Détection des pas activée pour nouvelle séquence")

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
        """
        Attend et enregistre la séquence de couleurs du joueur.
        Retourne la liste des couleurs détectées.
        S'arrête immédiatement si une erreur est détectée dans la séquence.
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
                
                # Vérifie si la couleur est correcte
                if couleur != self.etat.sequence[len(sequence)-1]:
                    print(f"\nErreur! Couleur attendue : {self.etat.sequence[len(sequence)-1]}")
                    print(f"Couleur reçue : {couleur}")
                    return sequence  # Retourne la séquence incomplète
                
                # Attend que le joueur ne soit plus sur une zone
                while not self.attendre_fin_pas():
                    pass
                
            except Exception as e:
                print("Temps écoulé!")
                break
            
        # Désactive la détection des pas après chaque séquence
        self.etat.peut_jouer = False
        print("Séquence terminée, détection des pas désactivée")
        logging.info("Détection des pas désactivée après séquence")
        return sequence

    def demarrer_jeu(self):
        """Boucle principale du jeu."""
        self.etat.reinitialiser()
        
        while True:
            # Crée et affiche une nouvelle séquence
            self.etat.sequence = self.creer_sequence(self.etat.sequence)
            self.afficher_sequence(self.etat.sequence)
            
            # Désactive la détection des pas jusqu'à l'événement objects-update
            self.etat.peut_jouer = False
            print("En attente de l'événement objects-update pour activer la prochaine séquence...")
            logging.info("En attente de l'événement objects-update")
            
            # Continue seulement quand etat.peut_jouer est mis à True par l'événement objects-update
            while not self.etat.peut_jouer:
                # Attend un court instant pour éviter de surcharger le CPU
                self.etat.pas_en_cours.wait(0.5)
            
            # Attend la réponse du joueur
            sequence_joueur = self.lire_sequence_joueur(len(self.etat.sequence))
            
            if not sequence_joueur:
                print("Partie terminée - Temps écoulé!")
                break
                
            # Vérifie si la séquence est complète et correcte
            if len(sequence_joueur) < len(self.etat.sequence):
                print(f"\nPartie terminée!")
                print(f"Séquence attendue : {' '.join(self.etat.sequence)}")
                print(f"Votre séquence   : {' '.join(sequence_joueur)} ❌")
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