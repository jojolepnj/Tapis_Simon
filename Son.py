import paho.mqtt.client as mqtt
from playsound import playsound
import time

class Son:
    def __init__(self, mqtt_broker, mqtt_port, topic):
        self.sequence = []
        self.topic = topic

        # Charger les chemins des fichiers sons
        self.sons = {
            0: "son/son0.mp3",
            1: "son/son1.mp3",
            2: "son/son2.mp3",
            3: "son/son3.mp3",
            4: "son/son4.mp3",
            5: "son/son5.mp3"
        }

        # Initialiser le client MQTT
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # Connecter au broker MQTT
        self.client.connect(mqtt_broker, mqtt_port, 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        print(f"Connecté avec le code de résultat {rc}")
        client.subscribe(self.topic)

    def on_message(self, client, userdata, msg):
        print(f"Message reçu sur le topic {msg.topic}: {msg.payload.decode()}")
        self.sequence = list(map(int, msg.payload.decode().split(',')))
        self.play_sequence()

    def play_sequence(self):
        for number in self.sequence:
            if number in self.sons:
                playsound(self.sons[number])
                time.sleep(1)  # Attendre une seconde entre les sons

if __name__ == "__main__":
    mqtt_broker = "192.168.1.102"
    mqtt_port = 1883
    topic = "Tapis/sequence"

    son = Son(mqtt_broker, mqtt_port, topic)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Déconnexion...")
        son.client.loop_stop()
        son.client.disconnect()