import unittest
from queue import Queue
from unittest.mock import Mock, patch
import pygame.mixer
from datetime import datetime
import json
from simon import JeuSimon, EtatJeu, Son

class TestEtatJeu(unittest.TestCase):
    def setUp(self):
        """Initialize test environment before each test"""
        self.etat = EtatJeu()

    def test_init(self):
        """Test initialization of EtatJeu"""
        self.assertEqual(self.etat.sequence, [])
        self.assertEqual(self.etat.score, 0)
        self.assertIsInstance(self.etat.couleurs, Queue)
        self.assertFalse(self.etat.peut_jouer)
        self.assertEqual(self.etat.position, 0)
        self.assertIsNone(self.etat.derniere_couleur_ajoutee)
        self.assertEqual(self.etat.derniere_detection, 0)
        self.assertIsNone(self.etat.derniere_couleur_detectee)

    def test_reinitialiser(self):
        """Test reset functionality"""
        self.etat.score = 10
        self.etat.sequence = ['rouge', 'vert']
        self.etat.derniere_couleur_detectee = 'bleu'
        
        self.etat.reinitialiser()
        
        self.assertEqual(self.etat.score, 0)
        self.assertEqual(self.etat.sequence, [])
        self.assertIsNone(self.etat.derniere_couleur_detectee)

    def test_ajouter_couleur(self):
        """Test color addition with time delay"""
        with patch('time.time') as mock_time:
            mock_time.return_value = 1.0
            self.etat.ajouter_couleur('rouge')
            self.assertEqual(self.etat.derniere_couleur_ajoutee, 'rouge')
            self.assertEqual(self.etat.position, 1)
            
            mock_time.return_value = 1.1
            self.etat.ajouter_couleur('rouge')
            self.assertEqual(self.etat.position, 1)
            
            mock_time.return_value = 1.6
            self.etat.ajouter_couleur('vert')
            self.assertEqual(self.etat.derniere_couleur_ajoutee, 'vert')
            self.assertEqual(self.etat.position, 2)

class TestJeuSimon(unittest.TestCase):
    @patch('pygame.mixer.init')
    @patch('pygame.mixer.Sound')
    @patch('pygame.mixer.set_num_channels')
    @patch('paho.mqtt.client.Client')
    def setUp(self, mock_mqtt, mock_set_channels, mock_sound, mock_mixer_init):
        """Initialize test environment before each test"""
        self.jeu = JeuSimon(mode_test=True)
        self.jeu.mqtt_client = Mock()

    def test_detecter_couleur(self):
        """Test color detection from coordinates"""
        self.assertEqual(self.jeu.detecter_couleur(0.2, 1.2), 'vert')
        self.assertEqual(self.jeu.detecter_couleur(0.2, 0.8), 'rouge')
        self.assertEqual(self.jeu.detecter_couleur(0.8, 1.2), 'jaune')
        self.assertEqual(self.jeu.detecter_couleur(0.8, 0.8), 'bleu')
        self.assertEqual(self.jeu.detecter_couleur(2.0, 2.0), 'inconnu')

    def test_convertir_sequence_en_chiffres(self):
        """Test sequence conversion from colors to numbers"""
        sequence = ['vert', 'rouge', 'bleu', 'jaune']
        expected = [0, 1, 2, 3]
        self.assertEqual(self.jeu.convertir_sequence_en_chiffres(sequence), expected)

    @patch('time.sleep', return_value=None)
    def test_publier_sequence_mqtt(self, mock_sleep):
        """Test MQTT sequence publication"""
        sequence = ['vert', 'rouge']
        self.jeu.publier_sequence_mqtt(sequence, 2, 0)
        self.jeu.mqtt_client.publish.assert_called_with(
            self.jeu.mqtt_topic,
            json.dumps({"couleur": [0, 1], "pas": True})
        )

        self.jeu.publier_sequence_mqtt(sequence, 3, 0)
        self.jeu.mqtt_client.publish.assert_called_with(
            self.jeu.mqtt_topic,
            json.dumps({"couleur": [4], "pas": False})
        )

    def test_difficulte(self):
        """Test difficulty settings"""
        self.jeu.changer_difficulte("facile")
        self.assertEqual(self.jeu.difficulte, "facile")
        
        self.jeu.changer_difficulte("invalid")
        self.assertEqual(self.jeu.difficulte, "facile")

    def test_reset_game(self):
        """Test game reset functionality"""
        self.jeu.game_started = True
        self.jeu.waiting_for_difficulty = True
        self.jeu.reset_game()
        self.assertFalse(self.jeu.game_started)
        self.assertFalse(self.jeu.waiting_for_difficulty)

class TestSon(unittest.TestCase):
    @patch('pygame.mixer.init')
    @patch('pygame.mixer.Sound')
    @patch('pygame.mixer.set_num_channels')
    @patch('paho.mqtt.client.Client')
    def setUp(self, mock_mqtt, mock_set_channels, mock_sound, mock_mixer_init):
        """Initialize test environment before each test"""
        self.son = Son(mqtt_client=Mock())

    def test_init(self):
        """Test Son class initialization"""
        self.assertEqual(self.son.topic, "Tapis/sequence")
        self.assertEqual(self.son.difficulty_topic, "site/difficulte")
        self.assertEqual(self.son.difficulty_level, 0)
        self.assertEqual(self.son.base_display_time, 2)

    @patch('time.sleep', return_value=None)
    def test_play_sequence(self, mock_sleep):
        """Test sequence playing"""
        sequence = [0, 1, 2]
        self.son.play_sequence(sequence)
        self.assertFalse(self.son.sound_queue.empty())
        self.assertEqual(self.son.sound_queue.get(), sequence)

if __name__ == '__main__':
    unittest.main(verbosity=2)