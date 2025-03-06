import socketio
import logging
import random
from queue import Queue
from threading import Event
from datetime import datetime

# Configuration du logger
logging.basicConfig(
    filename='log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# Configuration du client Socket.IO
sio = socketio.Client(
    reconnection=True,
    reconnection_attempts=5,
    reconnection_delay=1,
    reconnection_delay_max=5,
    logger=False,
    engineio_logger=False
)

# Variables globales pour le jeu
game_state = {
    'sequence': [],
    'score': 0,
    'current_color': None,
    'color_queue': Queue(),
    'waiting_for_input': Event(),
    'last_detected_color': None,
    'pending_color': None,      # Stocke la couleur en attente de validation
    'empty_data_received': False # Flag pour suivre si on a reçu une liste vide
}

def get_color(data):
    """Détermine la couleur en fonction des coordonnées"""
    birthX, birthY = data[0], data[1]
    
    if 0 <= birthX <= 0.5:
        return 'vert' if 1 <= birthY <= 1.5 else 'rouge'
    elif 0.5 < birthX <= 1:
        return 'jaune' if 1 <= birthY <= 1.5 else 'bleue'
    return 'inconnu'

def generate_sequence(previous_sequence):
    """Génère une nouvelle séquence"""
    colors = ['rouge', 'vert', 'bleue', 'jaune']
    if previous_sequence:
        colors = [c for c in colors if c != previous_sequence[-1]]
    return previous_sequence + [random.choice(colors)]

def display_sequence(sequence):
    """Affiche la séquence"""
    print(' '.join(sequence))
    print('\n' * 3)

@sio.event
def connect():
    """Gestion de la connexion"""
    logging.info("Connecté au serveur SensFloor")
    print("Connecté au serveur SensFloor")
    print("Bienvenue dans le jeu Simon !")
    start_game()

@sio.event
def disconnect():
    """Gestion de la déconnexion"""
    logging.info("Déconnecté du serveur")
    print("Déconnecté du serveur")

@sio.on('objects-update')
def on_objects_update(data):
    """Traitement des mises à jour avec validation sur liste vide"""
    if not game_state['waiting_for_input'].is_set():
        return

    if not data:  # Si la liste est vide
        if game_state['pending_color'] and not game_state['empty_data_received']:
            # Valide la couleur en attente si elle existe
            validated_color = game_state['pending_color']
            if validated_color != game_state['last_detected_color']:
                game_state['last_detected_color'] = validated_color
                game_state['color_queue'].put(validated_color)
                print(f"Couleur validée : {validated_color}")
            game_state['pending_color'] = None
            game_state['empty_data_received'] = True
    else:  # Si la liste contient des données
        position_data = [data[0]['birthX'], data[0]['birthY']]
        current_color = get_color(position_data)
        
        if current_color != 'inconnu':
            game_state['pending_color'] = current_color
            game_state['empty_data_received'] = False
            print(f"Couleur en attente : {current_color}")

def get_player_input(sequence_length):
    """Obtient l'entrée du joueur"""
    player_sequence = []
    game_state['waiting_for_input'].set()
    game_state['last_detected_color'] = None
    game_state['pending_color'] = None
    game_state['empty_data_received'] = False
    
    print("En attente de votre séquence...")
    print("Attendez la validation de chaque couleur avant de passer à la suivante.")
    
    while len(player_sequence) < sequence_length:
        try:
            color = game_state['color_queue'].get(timeout=20.0)
            player_sequence.append(color)

        except:
            print("Temps écoulé!")
            break
    
    game_state['waiting_for_input'].clear()
    return player_sequence

def start_game():
    """Boucle principale du jeu"""
    game_state['score'] = 0
    game_state['sequence'] = []
    
    
    while True:
        game_state['sequence'] = generate_sequence(game_state['sequence'])
        print("\nNouvelle séquence à reproduire:")
        display_sequence(game_state['sequence'])
        
        print("À vous de jouer!")
        player_sequence = get_player_input(len(game_state['sequence']))
        
        if not player_sequence:
            print("Temps écoulé - Fin de la partie!")
            break
            
        if player_sequence != game_state['sequence']:
            print(f"\nIncorrect! La séquence attendue était: {' '.join(game_state['sequence'])}")
            print(f"Votre séquence était: {' '.join(player_sequence)}")
            print(f"\nPartie terminée! Score final: {game_state['score']}")
            break
            
        game_state['score'] += 1
        print(f"\nBravo! Score actuel: {game_state['score']}")

if __name__ == "__main__":
    try:
        print("Connexion au serveur SensFloor...")
        sio.connect(
            'http://192.168.5.5:8000',
            transports=['websocket'],
            wait=True,
            wait_timeout=10
        )
        sio.wait()
    except Exception as e:
        logging.error(f"Erreur de connexion: {str(e)}")
        print(f"Erreur de connexion: {str(e)}")