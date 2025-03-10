#include <FastLED.h>
#include <M5Core2.h>

// Configuration des LEDs
#define NUM_LEDS 1024     // 4 matrices de 256 LEDs
#define DATA_PIN 33       // Pin GPIO connecté au fil de données (DIN) de la bande
#define LED_TYPE WS2812B  // Type de LED
#define COLOR_ORDER GRB   // Ordre des couleurs pour WS2812B

const uint8_t MATRIX_WIDTH = 16;
const uint8_t MATRIX_HEIGHT = 16;
const uint16_t MATRIX_SIZE = 256; // Taille d'une matrice

// Tableau pour stocker l'état des LEDs
CRGB leds[NUM_LEDS];

// Variables pour les animations
uint8_t gHue = 0;        // Teinte variable pour les animations
uint8_t mode = 0;        // Mode d'animation actuel

void clearAllMatrices() {
  FastLED.clear();
  FastLED.show();
}

void rainbow() {
  fill_rainbow(leds, NUM_LEDS, gHue, 8);
}

void rainbowWithGlitter() {
  rainbow();
  if (random8() < 80) {
    leds[random16(NUM_LEDS)] += CRGB::White;
  }
}

String choixCouleur(int colorChoice) {
  clearAllMatrices(); // Éteindre toutes les matrices avant d'allumer la nouvelle
  
  CRGB color;
  String couleur;
  uint16_t matrixOffset;
  
  switch (colorChoice) {
    case 0: // Vert - Première matrice
      color = CRGB::Green;
      couleur = "vert";
      matrixOffset = 0;
      break;
    case 1: // Rouge - Deuxième matrice
      color = CRGB::Red;
      couleur = "rouge";
      matrixOffset = MATRIX_SIZE;
      break;
    case 2: // Bleu - Troisième matrice
      color = CRGB::Blue;
      couleur = "bleu";
      matrixOffset = MATRIX_SIZE * 2;
      break;
    case 3: // Jaune - Quatrième matrice
      color = CRGB::Yellow;
      couleur = "jaune";
      matrixOffset = MATRIX_SIZE * 3;
      break;
    case 4: // Mode arc-en-ciel sur toutes les matrices
      couleur = "arc-en-ciel";
      rainbowWithGlitter();
      FastLED.show();
      EVERY_N_MILLISECONDS(20) { gHue++; }
      return couleur;
    default:
      color = CRGB::White;
      couleur = "défaut";
      matrixOffset = 0;
      break;
  }
  
  if (colorChoice <= 3) { // Pour les modes de couleur unique
    splash(color, matrixOffset);
  }
  
  EVERY_N_MILLISECONDS(20) { gHue++; }
  return couleur;
}

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
    FastLED.clear();
  }
  
  // Remplir la matrice entière à la fin de l'animation
  for (int i = 0; i < MATRIX_SIZE; i++) {
    leds[i + matrixOffset] = color;
  }
  FastLED.show();
}

uint16_t XY(uint8_t x, uint8_t y, uint16_t matrixOffset) {
  uint16_t i;
  if (y % 2 == 0) {
    // Even rows run forward
    i = (y * MATRIX_WIDTH) + x;
  } else {
    // Odd rows run backward
    i = (y * MATRIX_WIDTH) + (MATRIX_WIDTH - 1 - x);
  }
  return i + matrixOffset; // Ajouter l'offset pour sélectionner la bonne matrice
}

void setup() {
  M5.begin();
  Serial.begin(115200);
  
  // Configurer l'écran
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setCursor(0, 20);
  M5.Lcd.setTextColor(WHITE);
  M5.Lcd.setTextSize(2);
  M5.Lcd.println("WS2812B LED Demo");
  M5.Lcd.println("A: Changer mode");
  M5.Lcd.println("B: Luminosite +");
  M5.Lcd.println("C: Luminosite -");

  // Initialiser les LEDs
  FastLED.addLeds<LED_TYPE, DATA_PIN, COLOR_ORDER>(leds, NUM_LEDS).setCorrection(TypicalLEDStrip);
  FastLED.setBrightness(50);
  clearAllMatrices();
}

void loop() {
  M5.update();

  if (M5.BtnA.wasPressed()) {
    mode = (mode + 1) % 5;
    M5.Lcd.fillRect(0, 100, 320, 20, BLACK);
    M5.Lcd.setCursor(0, 100);
    M5.Lcd.print("Mode: ");
    String couleur = choixCouleur(mode);
    M5.Lcd.print(couleur);
  }

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