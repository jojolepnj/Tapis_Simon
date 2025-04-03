#include <M5Core2.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <FastLED.h>
#include <ArduinoJson.h>

// Configuration WiFi
const char* ssid = "Simon";
const char* password = "Simon1234";

// Configuration MQTT
const char* mqtt_server = "192.168.1.106";
const int mqtt_port = 1883;
const char* subscribe_topic = "Tapis/sequence";
const char* publish_topic = "LED/status";
uint8_t brightness = 5; 
// Teinte variable pour les animations
uint8_t gHue = 0; 
// Configuration MQTT - Ajout du nouveau topic
const char* difficulty_topic = "site/difficulte";

// Variables pour la difficulté
int difficulty_level = 0;  // 0=normal, 1=progressive, 2=accelerating
int base_display_time = 600; // Temps d'affichage de base
// Variables pour l'animation
int ANIMATION_DELAY = 50;  // Valeur par défaut
const int base_animation_delay = 50; // Délai d'animation de base


// Configuration des LEDs
#define NUM_LEDS 1024     // 4 matrices de 256 LEDs
#define DATA_PIN 33       // Pin GPIO connecté au fil de données (DIN)
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB
#define NUM_MATRICES 4

const uint8_t MATRIX_WIDTH = 16;
const uint8_t MATRIX_HEIGHT = 16;
const uint16_t MATRIX_SIZE = 256;       
const int DISPLAY_TIME = 600;             // Temps d'affichage pour chaque couleur (en ms)

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

uint16_t XY(uint8_t x, uint8_t y, uint16_t matrixOffset = 0);
void setup_wifi();
void callback(char* topic, byte* payload, unsigned int length);
void reconnect();

//Fonctions d'animation
void splash(CRGB color, uint16_t matrixOffset);
void Anim_Erreur();
void horizontalLinesAnimation(CRGB lineColor, uint16_t matrixOffset);
void squareWaveAnimation(CRGB squareColor, uint16_t matrixOffset);
void snailAnimation(CRGB lineColor, uint16_t matrixOffset);
void displayProgressivePlus(CRGB color, uint16_t matrixOffset); 

void setAnimationDelays(float speed_factor) {
    // Ajuster les délais dans les fonctions d'animation
    ANIMATION_DELAY = base_animation_delay * speed_factor;
    // Vous pouvez ajouter d'autres ajustements de délai ici pour les autres animations
}

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

    // Gestion des messages de difficulté
    if (String(topic) == difficulty_topic) {
       Serial.println("Message reçu sur le topic difficulté");
       Serial.println("Message: " + message);
    
    if (doc.containsKey("dif")) {
        int new_difficulty = doc["dif"].as<int>();
        // Validation de la valeur de difficulté
        if (new_difficulty >= 0 && new_difficulty <= 2) {
            difficulty_level = new_difficulty;
            M5.Lcd.fillScreen(BLACK);
            M5.Lcd.setCursor(0, 0);
            M5.Lcd.printf("Niveau de difficulte: %d\n", difficulty_level);
            Serial.printf("Difficulté mise à jour: %d\n", difficulty_level);
        } else {
            Serial.println("Valeur de difficulté invalide");
            M5.Lcd.println("Difficulté invalide");
        }
    } else {
        Serial.println("Champ 'dif' manquant dans le JSON");
        M5.Lcd.println("Format JSON invalide");
    }
    return;
}

    // Gestion des messages de séquence (code existant)
    if (String(topic) == subscribe_topic) {
        // Vérifier la présence des deux champs requis
        if (!doc.containsKey("couleur") || !doc.containsKey("pas")) {
            M5.Lcd.println("JSON invalide");
            Serial.println("JSON invalide - champs manquants");
            return;
        }
        
        pas = doc["pas"].as<bool>();
        etat = pas ? 1 : 0;

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

        if (client.connect(clientId.c_str())) {
            M5.Lcd.println("Connecté au MQTT!");
            // Souscrire aux deux topics
            client.subscribe(subscribe_topic);
            client.subscribe(difficulty_topic);  // Ajout de la souscription au topic de difficulté
            
            M5.Lcd.println("Abonné aux topics:");
            M5.Lcd.println(subscribe_topic);
            M5.Lcd.println(difficulty_topic);
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
    FastLED.setBrightness(brightness);
    clearAllMatrices();

    setup_wifi();
    client.setServer(mqtt_server, mqtt_port);
    client.setCallback(callback);
    
    // Souscrire aux deux topics
    client.subscribe(subscribe_topic);
    client.subscribe(difficulty_topic);  // Ajout de la souscription au topic de difficulté
}

void loop() {
    M5.update();

    if (!client.connected()) {
        reconnect();
    }
    client.loop();

    if (M5.BtnB.wasPressed()) {
        brightness = FastLED.getBrightness();
        brightness = brightness + 10 > 255 ? 255 : brightness + 10;
        FastLED.setBrightness(brightness);
        M5.Lcd.fillRect(0, 120, 320, 20, BLACK);
        M5.Lcd.setCursor(0, 120);
        M5.Lcd.print("Luminosite: ");
        M5.Lcd.print(brightness);
    }

    if (M5.BtnC.wasPressed()) {
        brightness = FastLED.getBrightness();
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
        case 0:  // Vert (bas droite)
            color = CRGB::Green;
            matrixOffset = 0;
            horizontalLinesAnimation(color, matrixOffset);
            break;
        case 1:  // Rouge (haut droite)
            color = CRGB::Red;
            matrixOffset = MATRIX_SIZE;
            squareWaveAnimation(color, matrixOffset);
            break;
        case 2:  // Bleu (haut gauche)
            color = CRGB::Blue;
            matrixOffset = MATRIX_SIZE * 2;
            displayProgressivePlus(color, matrixOffset);
            // Pas besoin d'appeler FastLED.show() ici car déjà fait dans snailAnimation
            break;
        case 3:  // Jaune (bas gauche)
            color = CRGB::Yellow;
            matrixOffset = MATRIX_SIZE * 3;
            splash(color, matrixOffset);
            break;
        case 4:  // Croix /erreur
            Anim_Erreur();
            delay(5000);
            break;
        case 5:
            fill_solid(leds, NUM_LEDS, CRGB::White);
            FastLED.show();
            delay(2000);
            clearAllMatrices();
            break;
        default:
            return;
  }
}

void playSequence() {
    client.publish(publish_topic, "true");
    int current_display_time = base_display_time;
    float animation_speed_factor = 1.0;

    // Calcul du temps d'affichage en fonction de la difficulté
    if (difficulty_level == 1) {
        // Mode progressif - réduit le temps tous les 5 éléments
        int sequence_multiple = (colorSequence.size() - 1) / 5;
        if (sequence_multiple > 0) {
            animation_speed_factor = 1.0 / (1 + (sequence_multiple * 0.2)); // Réduit de 20% par multiple de 5
            current_display_time *= animation_speed_factor;
        }
    }

    // Afficher le blanc avant une séquence à reproduire comme séparateur
    if (pas) {
        displayColor(5);
        delay(current_display_time);
    }

    // Jouer la séquence de couleurs
    for (size_t i = 0; i < colorSequence.size(); i++) {
        if (difficulty_level == 2) {
            // Mode accéléré - réduit le temps à chaque tour
            animation_speed_factor = 1.0 / (1 + (i * 0.1)); // Réduit de 10% à chaque étape
            current_display_time = base_display_time * animation_speed_factor;
        }

        // Ajuster les délais d'animation
        setAnimationDelays(animation_speed_factor);
        
        displayColor(colorSequence[i]);
        delay(current_display_time);
        clearAllMatrices();
    }

    // Afficher le blanc uniquement après une séquence à reproduire
    if (pas) {
        displayColor(5);
        delay(current_display_time);
    }

    isPlayingSequence = false;
    colorSequence.clear();
    client.publish(publish_topic, "false");
}

void Anim_Erreur() {
    // Effacer toutes les LEDs
    clearAllMatrices();
    
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
void horizontalLinesAnimation(CRGB lineColor, uint16_t matrixOffset) {
    clearAllMatrices();

    // Pour chaque colonne (de gauche à droite)
    for(int x = 0; x < MATRIX_WIDTH; x++) {
        // Dessiner toutes les lignes horizontales en même temps
        for(int y = 0; y < MATRIX_HEIGHT; y += 4) {
            // Allumer 2 lignes consécutives
            for(int thickness = 0; thickness < 2; thickness++) {
                if((y + thickness) < MATRIX_HEIGHT) {
                    leds[XY(x, y + thickness, matrixOffset)] = lineColor;
                }
            }
        }
        FastLED.show();
        delay(ANIMATION_DELAY);
    }
}

void squareWaveAnimation(CRGB squareColor, uint16_t matrixOffset) {
    // Effacer la matrice
    clearAllMatrices();
    
    const uint8_t SQUARE_SIZE = 2;      // Taille de chaque carré
    const uint8_t SPACING = 4;          // Espacement entre les carrés
    const uint8_t BORDER_OFFSET = 1;    // Décalage par rapport au bord
    const int TOTAL_STEPS = 16;         // Nombre total d'étapes
    const int STEP_DELAY = 400 / TOTAL_STEPS;  // Délai entre chaque étape
    
    // Animation diagonale
    for(uint8_t step = 0; step < TOTAL_STEPS; step++) {
        for(uint8_t y = BORDER_OFFSET; y < MATRIX_HEIGHT - BORDER_OFFSET; y += SPACING) {
            for(uint8_t x = BORDER_OFFSET; x < MATRIX_WIDTH - BORDER_OFFSET; x += SPACING) {
                // Si cette position doit être allumée dans cette étape
                if(((x-BORDER_OFFSET)/SPACING + (y-BORDER_OFFSET)/SPACING) == step/2) {
                    // Dessiner un carré 2x2
                    for(uint8_t dx = 0; dx < SQUARE_SIZE; dx++) {
                        for(uint8_t dy = 0; dy < SQUARE_SIZE; dy++) {
                            if((x + dx < MATRIX_WIDTH - BORDER_OFFSET) && 
                               (y + dy < MATRIX_HEIGHT - BORDER_OFFSET)) {
                                leds[Coord_LEDs_Erreur(x + dx, y + dy, matrixOffset)] = squareColor;
                            }
                        }
                    }
                }
            }
        }
        FastLED.show();
        delay(STEP_DELAY);
    }
}
// Version corrigée de snailAnimation
void snailAnimation(CRGB lineColor, uint16_t matrixOffset) {
    // Effacer la matrice
    clearAllMatrices();

    // Réduire le nombre de points et le délai pour une animation plus rapide
    const uint8_t totalPoints = 50;    // Légèrement réduit de 60 à 50
    const int delayTime = 2;          // Réduit de 25 à 15ms

    // Centre de la matrice
    const uint8_t centerX = 8;
    const uint8_t centerY = 8;

    float radius = 0.0;
    float angle = 0.0;

    for(uint8_t i = 0; i < totalPoints; i++) {
        // Calculer les coordonnées du point actuel
        uint8_t x = centerX + (uint8_t)(radius * cos(angle));
        uint8_t y = centerY + (uint8_t)(radius * sin(angle));

        // Vérifier les limites
        if(x < MATRIX_WIDTH && y < MATRIX_HEIGHT) {
            leds[Coord_LEDs_Erreur(x, y, matrixOffset)] = lineColor;
            FastLED.show();
            delay(delayTime);
        }
        // Garder les mêmes valeurs pour la forme de la spirale
        angle += 0.4;
        radius += 0.12;
    }
}
void displayProgressivePlus(CRGB color, uint16_t matrixOffset) {
    const uint8_t MATRIX_SIZE = 16;
    const uint8_t LINE_THICKNESS = 4;
    const uint8_t CENTER = MATRIX_SIZE / 2 - LINE_THICKNESS / 2;
    
    // Pour chaque étape de l'animation
    for (uint8_t step = 0; step <= MATRIX_SIZE / 2; step++) {
        // Dessiner la ligne verticale
        for (uint8_t thickness = 0; thickness < LINE_THICKNESS; thickness++) {
            // Partie supérieure
            if (step > 0) {
                for (uint8_t y = CENTER - step; y < CENTER; y++) {
                    uint16_t index = (y * MATRIX_SIZE + (CENTER + thickness)) + matrixOffset;
                    leds[index] = color;  // Changé matrix[index] en leds[index]
                }
            }
            // Partie inférieure
            if (step > 0) {
                for (uint8_t y = CENTER + LINE_THICKNESS; y <= CENTER + step; y++) {
                    uint16_t index = (y * MATRIX_SIZE + (CENTER + thickness)) + matrixOffset;
                    leds[index] = color;  // Changé matrix[index] en leds[index]
                }
            }
        }
        // Dessiner la ligne horizontale
        for (uint8_t thickness = 0; thickness < LINE_THICKNESS; thickness++) {
            // Partie gauche
            if (step > 0) {
                for (uint8_t x = CENTER - step; x < CENTER; x++) {
                    uint16_t index = ((CENTER + thickness) * MATRIX_SIZE + x) + matrixOffset;
                    leds[index] = color;  // Changé matrix[index] en leds[index]
                }
            }
            // Partie droite
            if (step > 0) {
                for (uint8_t x = CENTER + LINE_THICKNESS; x <= CENTER + step; x++) {
                    uint16_t index = ((CENTER + thickness) * MATRIX_SIZE + x) + matrixOffset;
                    leds[index] = color;  // Changé matrix[index] en leds[index]
                }
            }
        }
        // Centre du plus
        for (uint8_t i = 0; i < LINE_THICKNESS; i++) {
            for (uint8_t j = 0; j < LINE_THICKNESS; j++) {
                uint16_t index = ((CENTER + i) * MATRIX_SIZE + (CENTER + j)) + matrixOffset;
                leds[index] = color;  // Changé matrix[index] en leds[index]
            }
        }
        FastLED.show();
        delay(50); // Délai entre chaque étape de l'animation
    }
}