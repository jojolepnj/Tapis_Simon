#include <M5Core2.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <FastLED.h>
#include <ArduinoJson.h>

// Configuration WiFi
const char* ssid = "Simon";
const char* password = "Simon1234";

// Configuration MQTT
const char* mqtt_server = "192.168.1.102";
const int mqtt_port = 1883;
const char* subscribe_topic = "Tapis/sequence";
const char* publish_topic = "LED/status";
int brightness = 5; 
// Teinte variable pour les animations
uint8_t gHue = 0; 

// Configuration des LEDs
#define NUM_LEDS 1024     // 4 matrices de 256 LEDs
#define DATA_PIN 33       // Pin GPIO connecté au fil de données (DIN)
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB
#define NUM_MATRICES 4

const uint8_t MATRIX_WIDTH = 16;
const uint8_t MATRIX_HEIGHT = 16;
const uint16_t MATRIX_SIZE = 256;       
const int DISPLAY_TIME = 1000;             // Temps d'affichage pour chaque couleur (en ms)

// Variables globales pour le contrôle de l'état
bool pas = false;
uint8_t etat = 0;
// Tableau pour stocker l'état des LEDs
CRGB leds[NUM_LEDS];

WiFiClient espClient;
PubSubClient client(espClient);

// Variables pour la séquence
std::vector<int> colorSequence;
bool isPlayingSequence = false;

// Déclarations anticipées des fonctions
void clearAllMatrices();
void displayColor(int colorChoice);
void playSequence();
void Anim_Erreur();
uint16_t XY(uint8_t x, uint8_t y, uint16_t matrixOffset = 0);
void setup_wifi();
void callback(char* topic, byte* payload, unsigned int length);
void reconnect();
void splash(CRGB color, uint16_t matrixOffset);

void setup_wifi() {
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setCursor(0, 0);
    M5.Lcd.println("Connecting to WiFi...");
    M5.Lcd.print("SSID: ");
    M5.Lcd.println(ssid);

    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        M5.Lcd.print(".");
    }

    M5.Lcd.println("\nWiFi connected!");
    M5.Lcd.println("-------------------");
    M5.Lcd.print("IP address: ");
    M5.Lcd.println(WiFi.localIP().toString());
    M5.Lcd.println("-------------------");
    delay(2000);

    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setCursor(0, 20);
    M5.Lcd.println("LED Matrix MQTT Controller");
}

void callback(char* topic, byte* payload, unsigned int length) {
    String message;
    for (int i = 0; i < length; i++) {
        message += (char)payload[i];
    }

    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, message);

    if (error) {
        M5.Lcd.println("Erreur de parsing JSON");
        Serial.println("Erreur de parsing JSON");
        return;
    }
    
    // Vérifier la présence des deux champs requis
    if (!doc.containsKey("couleur") || !doc.containsKey("pas")) {
        M5.Lcd.println("JSON invalide");
        Serial.println("JSON invalide - champs manquants");
        return;
    }
    
    // Traitement du champ "pas"
    pas = doc["pas"].as<bool>();
    etat = pas ? 1 : 0;  // Mise à jour de l'état en fonction de pas

    colorSequence.clear();

    JsonArray array = doc["couleur"].as<JsonArray>();
    for (JsonVariant v : array) {
        colorSequence.push_back(v.as<int>());
    }

    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setCursor(0, 0);
    M5.Lcd.println(pas ? "Sequence a reproduire:" : "Sequence jouee:");
    M5.Lcd.print("[ ");
    for (int color : colorSequence) {
        M5.Lcd.print(color);
        M5.Lcd.print(" ");
    }
    M5.Lcd.println("]");

    if (!isPlayingSequence && colorSequence.size() > 0) {
        isPlayingSequence = true;
        client.publish(publish_topic, "false");
        playSequence();
    }
}

void reconnect() {
    int tentatives = 0;
    while (!client.connected() && tentatives < 3) {
        tentatives++;
        M5.Lcd.fillScreen(BLACK);
        M5.Lcd.setCursor(0, 0);
        M5.Lcd.printf("Tentative MQTT %d/3...\n", tentatives);

        String clientId = "M5Stack-";
        clientId += String(random(0xffff), HEX);

        M5.Lcd.printf("Server: %s\n", mqtt_server);
        M5.Lcd.printf("Port: %d\n", mqtt_port);
        M5.Lcd.printf("Topic: %s\n", subscribe_topic);

        if (client.connect(clientId.c_str())) {
            M5.Lcd.println("Connecté au MQTT!");
            client.subscribe(subscribe_topic);
            M5.Lcd.println("Abonné au topic:");
            M5.Lcd.println(subscribe_topic);
        } else {
            M5.Lcd.printf("Échec, erreur: %d\n", client.state());
            M5.Lcd.println("Nouvelle tentative...");
            delay(5000);
        }
    }
}

void setup() {
    M5.begin();
    Serial.begin(115200);

    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setTextColor(WHITE);
    M5.Lcd.setTextSize(2);
    M5.Lcd.setCursor(0, 20);
    M5.Lcd.println("LED Matrix MQTT Controller");

    FastLED.addLeds<LED_TYPE, DATA_PIN, COLOR_ORDER>(leds, NUM_LEDS)
        .setCorrection(TypicalLEDStrip);
    FastLED.setBrightness(25);
    clearAllMatrices();

    setup_wifi();
    client.setServer(mqtt_server, mqtt_port);
    client.setCallback(callback);
}

void loop() {
    M5.update();

    if (!client.connected()) {
        reconnect();
    }
    client.loop();

    if (M5.BtnB.wasPressed()) {
        uint8_t brightness = FastLED.getBrightness();
        brightness = brightness + 10 > 255 ? 255 : brightness + 10;
        FastLED.setBrightness(brightness);
        M5.Lcd.fillRect(0, 120, 320, 20, BLACK);
        M5.Lcd.setCursor(0, 120);
        M5.Lcd.print("Luminosite: ");
        M5.Lcd.print(brightness);
    }

    if (M5.BtnC.wasPressed()) {
        uint8_t brightness = FastLED.getBrightness();
        brightness = brightness - 10 < 0 ? 0 : brightness - 10;
        FastLED.setBrightness(brightness);
        M5.Lcd.fillRect(0, 120, 320, 20, BLACK);
        M5.Lcd.setCursor(0, 120);
        M5.Lcd.print("Luminosite: ");
        M5.Lcd.print(brightness);
    }
}

void clearAllMatrices() {
    FastLED.clear();
    FastLED.show();
}

uint16_t XY(uint8_t x, uint8_t y, uint16_t matrixOffset) {
    if (x >= MATRIX_WIDTH || y >= MATRIX_HEIGHT) return 0;
    return (y * MATRIX_WIDTH + x) + matrixOffset;
}
uint16_t Coord_LEDs_Erreur(uint8_t x, uint8_t y, uint16_t matrixOffset) {
    if (x >= MATRIX_WIDTH || y >= MATRIX_HEIGHT) return 0;
    
    uint16_t i;
    if(y & 0x01) {  // Lignes impaires
        uint8_t reverseX = (MATRIX_WIDTH - 1) - x;
        i = (y * MATRIX_WIDTH) + reverseX;
    } else {        // Lignes paires
        i = (y * MATRIX_WIDTH) + x;
    }
    
    return i + matrixOffset;
}
// Animation d'expansion pour l'affichage des couleurs
void splash(CRGB color, uint16_t matrixOffset) {
  for (uint8_t size = 2; size <= MATRIX_WIDTH; size += 2) {
    int centerX = MATRIX_WIDTH / 2;
    int centerY = MATRIX_HEIGHT / 2;
    int startX = centerX - size / 2;
    int startY = centerY - size / 2;
    int endX = startX + size;
    int endY = startY + size;

    for (int x = startX; x < endX; ++x) {
      for (int y = startY; y < endY; ++y) {
        if (x >= 0 && x < MATRIX_WIDTH && y >= 0 && y < MATRIX_HEIGHT) {
          leds[XY(x, y, matrixOffset)] = color;
        }
      }
    }
    FastLED.show();
    delay(50);
    
  }

  // Remplir la matrice entière à la fin de l'animation
  for (int i = 0; i < MATRIX_SIZE; i++) {
    leds[i + matrixOffset] = color;
  }
  FastLED.show();
}

// Modifier la fonction displayColor pour utiliser splash
void displayColor(int colorChoice) {
  clearAllMatrices();

  CRGB color;
  uint16_t matrixOffset;

  switch (colorChoice) {
    case 0:  // Vert
      color = CRGB::Green;
      matrixOffset = 0;
      break;
    case 1:  // Rouge
      color = CRGB::Red;
      matrixOffset = MATRIX_SIZE;
      break;
    case 2:  // Bleu
      color = CRGB::Blue;
      matrixOffset = MATRIX_SIZE * 2;
      break;
    case 3:  // Jaune
      color = CRGB::Yellow;
      matrixOffset = MATRIX_SIZE * 3;
      break;
    case 4:  // Croix /erreur
      Anim_Erreur();
      delay(5000);
      break;
    case 5:
     FastLED.setBrightness(5);
      fill_solid(leds, NUM_LEDS, CRGB::White);
      FastLED.show();
      delay(2000);
      clearAllMatrices();
      break;
    default:
      return;
  }

  if (colorChoice < 4) {
      splash(color, matrixOffset);
      FastLED.setBrightness(brightness);
      FastLED.show();
    }// Utiliser splash au lieu de remplir directement

}

void playSequence() {
    client.publish(publish_topic, "true");

    // Jouer la séquence de couleurs
    for (int color : colorSequence) {
        displayColor(color);
        delay(DISPLAY_TIME);
        clearAllMatrices();
    }

    // Afficher le blanc uniquement après une séquence à reproduire
    if (pas) {  // On utilise directement pas au lieu de etat
        displayColor(5);  // Affichage en blanc
        delay(DISPLAY_TIME);
    }

    isPlayingSequence = false;
    colorSequence.clear();
    client.publish(publish_topic, "false");
    FastLED.setBrightness(brightness);
}

void Anim_Erreur() {
    // Effacer toutes les LEDs
    FastLED.clear();
    FastLED.setBrightness(25);
    
    // Pour les matrices 3 et 4 (diagonales montantes)
    for(int matrix : {2, 3}) {
        int matrixOffset = matrix * MATRIX_SIZE;
        
        for(int i = 0; i < MATRIX_WIDTH; i++) {
            int y = MATRIX_HEIGHT-1-i;
            
            // Diagonale centrale (orange vif)
            leds[Coord_LEDs_Erreur(i, y, matrixOffset)] = CRGB(255, 69, 0);  // Orange vif
            
            // Première paire de diagonales (orange légèrement plus clair)
            if(i > 0) {
                leds[Coord_LEDs_Erreur(i-1, y, matrixOffset)] = CRGB(255, 120, 0);
            }
            if(i < MATRIX_WIDTH-1) {
                leds[Coord_LEDs_Erreur(i+1, y, matrixOffset)] = CRGB(255, 120, 0);
            }
            
            // Deuxième paire de diagonales (jaune vif)
            if(i > 1) {
                leds[Coord_LEDs_Erreur(i-2, y, matrixOffset)] = CRGB(255, 255, 0);  // Jaune pur
            }
            if(i < MATRIX_WIDTH-2) {
                leds[Coord_LEDs_Erreur(i+2, y, matrixOffset)] = CRGB(255, 255, 0);  // Jaune pur
            }
        }
    }
    
    // Pour les matrices 1 et 2 (diagonales descendantes)
    for(int matrix : {0, 1}) {
        int matrixOffset = matrix * MATRIX_SIZE;
        
        for(int i = 0; i < MATRIX_WIDTH; i++) {
            // Diagonale centrale (orange vif)
            leds[Coord_LEDs_Erreur(i, i, matrixOffset)] = CRGB(255, 69, 0);  // Orange vif
            
            // Première paire de diagonales (orange légèrement plus clair)
            if(i > 0) {
                leds[Coord_LEDs_Erreur(i-1, i, matrixOffset)] = CRGB(255, 120, 0);
            }
            if(i < MATRIX_WIDTH-1) {
                leds[Coord_LEDs_Erreur(i+1, i, matrixOffset)] = CRGB(255, 120, 0);
            }
            
            // Deuxième paire de diagonales (jaune vif)
            if(i > 1) {
                leds[Coord_LEDs_Erreur(i-2, i, matrixOffset)] = CRGB(255, 255, 0);  // Jaune pur
            }
            if(i < MATRIX_WIDTH-2) {
                leds[Coord_LEDs_Erreur(i+2, i, matrixOffset)] = CRGB(255, 255, 0);  // Jaune pur
            }
        }
    }
    
    FastLED.show();
}