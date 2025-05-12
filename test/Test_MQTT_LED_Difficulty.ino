#include <FastLED.h>
#include <M5Core2.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// Désactiver la macro test de FastLED
#ifdef test
#undef test
#endif

#include <AUnitVerbose.h>

using namespace aunit;

// ============= Configuration =============
#define NUM_LEDS 1024
#define DATA_PIN 33
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB
#define NUM_MATRICES 4
#define MATRIX_WIDTH 16
#define MATRIX_HEIGHT 16
#define MATRIX_SIZE 256

// ============= Mocks =============
namespace TestMocks {
    class WiFiMock {
    public:
        static bool connectCalled;
        static int status;
        static void begin(const char* ssid, const char* password) {
            connectCalled = true;
            status = WL_CONNECTED;
        }
        static int getStatus() { return status; }
    };

    class MQTTMock {
    public:
        static bool publishCalled;
        static bool subscribeCalled;
        static bool connectCalled;
        static bool connected;
        
        static void reset() {
            publishCalled = false;
            subscribeCalled = false;
            connectCalled = false;
            connected = false;
        }
        
        static bool publish(const char* topic, const char* payload) {
            publishCalled = true;
            return true;
        }
        
        static bool connect(const char* clientId) {
            connectCalled = true;
            connected = true;
            return true;
        }
        
        static bool isConnected() { return connected; }
    };
}

// Initialisation des variables statiques des mocks
bool TestMocks::WiFiMock::connectCalled = false;
int TestMocks::WiFiMock::status = WL_IDLE_STATUS;
bool TestMocks::MQTTMock::publishCalled = false;
bool TestMocks::MQTTMock::subscribeCalled = false;
bool TestMocks::MQTTMock::connectCalled = false;
bool TestMocks::MQTTMock::connected = false;

// ============= Variables Globales =============
CRGB leds[NUM_LEDS];
uint8_t brightness = 5;
uint8_t gHue = 0;
int difficulty_level = 0;
int base_display_time = 600;
int ANIMATION_DELAY = 50;
const int base_animation_delay = 50;
bool pas = false;
uint8_t etat = 0;
std::vector<int> colorSequence;
bool isPlayingSequence = false;
WiFiClient espClient;
PubSubClient client(espClient);

const char* ssid = "Simon";
const char* password = "Simon1234";
const char* mqtt_server = "192.168.1.106";
const int mqtt_port = 1883;
const char* subscribe_topic = "Tapis/sequence";
const char* publish_topic = "LED/status";
const char* difficulty_topic = "site/difficulte";

// ============= Déclarations des fonctions =============
void clearAllMatrices();
uint16_t XY(uint8_t x, uint8_t y, uint16_t matrixOffset = 0);
void displayColor(int colorChoice);
void callback(char* topic, byte* payload, unsigned int length);
void setAnimationDelays(float speed_factor);
void splash(CRGB color, uint16_t matrixOffset);
void horizontalLinesAnimation(CRGB lineColor, uint16_t matrixOffset);
void squareWaveAnimation(CRGB squareColor, uint16_t matrixOffset);

// ============= Classe de Test =============
class MatrixTest : public TestOnce {
protected:
    void setup() override {
        TestOnce::setup();
        FastLED.addLeds<LED_TYPE, DATA_PIN, COLOR_ORDER>(leds, NUM_LEDS)
               .setCorrection(TypicalLEDStrip);
        FastLED.setBrightness(brightness);
        clearAllMatrices();
        TestMocks::MQTTMock::reset();
    }

    void teardown() override {
        TestOnce::teardown();
        clearAllMatrices();
        colorSequence.clear();
    }
};

// ============= Tests =============
// Test des fonctions de base
testF(MatrixTest, BasicFunctionsTest) {
    // Test clearAllMatrices
    fill_solid(leds, NUM_LEDS, CRGB::Red);
    clearAllMatrices();
    assertEqual(leds[0].r, 0);
    assertEqual(leds[0].g, 0);
    assertEqual(leds[0].b, 0);

    // Test XY function
    assertEqual(XY(0, 0, 0), 0);
    assertEqual(XY(MATRIX_WIDTH-1, MATRIX_HEIGHT-1, 0), MATRIX_SIZE-1);
}

// Test des animations
testF(MatrixTest, AnimationsTest) {
    // Test splash animation
    splash(CRGB::Red, 0);
    assertTrue(leds[0].r > 0);
    delay(100);
    clearAllMatrices();

    // Test horizontal lines
    horizontalLinesAnimation(CRGB::Blue, 0);
    assertTrue(leds[0].b > 0);
    delay(100);
    clearAllMatrices();

    // Test square wave
    squareWaveAnimation(CRGB::Green, 0);
    assertTrue(leds[0].g > 0);
    delay(100);
    clearAllMatrices();
}

// Test MQTT callbacks
testF(MatrixTest, MQTTTest) {
    // Test valid JSON
    const char* validJson = R"({"couleur":[0,1,2],"pas":true})";
    byte validPayload[100];
    memcpy(validPayload, validJson, strlen(validJson));
    
    callback(const_cast<char*>(subscribe_topic), validPayload, strlen(validJson));
    assertEqual(colorSequence.size(), 3u);
    assertTrue(pas);

    // Test invalid JSON
    const char* invalidJson = R"({"invalid":})";
    byte invalidPayload[100];
    memcpy(invalidPayload, invalidJson, strlen(invalidJson));
    
    size_t initialSize = colorSequence.size();
    callback(const_cast<char*>(subscribe_topic), invalidPayload, strlen(invalidJson));
    assertEqual(colorSequence.size(), initialSize);
}

// Test des niveaux de difficulté
testF(MatrixTest, DifficultyTest) {
    int initial_delay = ANIMATION_DELAY;
    
    // Test progressive difficulty
    difficulty_level = 1;
    setAnimationDelays(0.8);
    assertTrue(ANIMATION_DELAY < initial_delay);
    
    // Test accelerating difficulty
    difficulty_level = 2;
    setAnimationDelays(0.5);
    assertTrue(ANIMATION_DELAY < initial_delay);
}

// Test du contrôle de la luminosité
testF(MatrixTest, BrightnessTest) {
    uint8_t initial_brightness = FastLED.getBrightness();
    
    // Test increase
    if (brightness + 10 <= 255) {
        brightness += 10;
        FastLED.setBrightness(brightness);
        assertEqual(FastLED.getBrightness(), initial_brightness + 10);
    }
    
    // Test decrease
    if (brightness >= 10) {
        brightness -= 10;
        FastLED.setBrightness(brightness);
        assertEqual(FastLED.getBrightness(), initial_brightness);
    }
}

// ============= Setup et Loop =============
void setup() {
    Serial.begin(115200);
    while(!Serial); // Attendre que le port série soit prêt
    
    M5.begin();
    
    TestRunner::exclude("*");
    TestRunner::include("MatrixTest*");
}

void loop() {
    TestRunner::run();
    delay(1);
}

// ============= Implémentation des fonctions =============
void clearAllMatrices() {
    FastLED.clear();
    FastLED.show();
}

uint16_t XY(uint8_t x, uint8_t y, uint16_t matrixOffset) {
    if (x >= MATRIX_WIDTH || y >= MATRIX_HEIGHT) return 0;
    return (y * MATRIX_WIDTH + x) + matrixOffset;
}

void setAnimationDelays(float speed_factor) {
    ANIMATION_DELAY = base_animation_delay * speed_factor;
}

// Implémentations simplifiées pour les tests
void splash(CRGB color, uint16_t matrixOffset) {
    leds[matrixOffset] = color;
    FastLED.show();
}

void horizontalLinesAnimation(CRGB lineColor, uint16_t matrixOffset) {
    leds[matrixOffset] = lineColor;
    FastLED.show();
}

void squareWaveAnimation(CRGB squareColor, uint16_t matrixOffset) {
    leds[matrixOffset] = squareColor;
    FastLED.show();
}

void callback(char* topic, byte* payload, unsigned int length) {
    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, payload, length);
    
    if (error) {
        return;
    }
    
    if (doc.containsKey("couleur") && doc.containsKey("pas")) {
        pas = doc["pas"].as<bool>();
        JsonArray array = doc["couleur"].as<JsonArray>();
        colorSequence.clear();
        for (JsonVariant v : array) {
            colorSequence.push_back(v.as<int>());
        }
    }
}