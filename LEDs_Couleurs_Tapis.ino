#include <FastLED.h>
#include <M5Core2.h>

// Configuration des LEDs
#define NUM_LEDS 256      // Nombre de LEDs dans votre bande - à ajuster selon votre configuration
#define DATA_PIN 33     // Pin GPIO connecté au fil de données (DIN) de la bande
#define LED_TYPE WS2812B // Type de LED
#define COLOR_ORDER GRB  // Ordre des couleurs pour WS2812B

const uint8_t MATRIX_WIDTH = 16;
const uint8_t MATRIX_HEIGHT = 16;

// Tableau pour stocker l'état des LEDs
CRGB leds[NUM_LEDS];

// Variables pour les animations
uint8_t gHue = 0;        // Teinte variable pour les animations
uint8_t mode = 0;        // Mode d'animation actuel

void rainbow() {
  fill_rainbow(leds, NUM_LEDS, gHue, 7);
}
void rainbowWithGlitter() {
  rainbow();
  if (random8() < 80) {
    leds[random16(NUM_LEDS)] += CRGB::White;
  }
}


String choixCouleur(int colorChoice){
  
 CRGB color;
 String couleur;
  switch (colorChoice) {
    case 0:
      color = CRGB::Red;
      couleur = "rouge";
      splash(color);
      break;
    case 1:
      color = CRGB::Blue;
      couleur = "bleu";
      splash(color);
      break;
    case 2:
      color = CRGB::Green;
      couleur = "vert";
      splash(color);
      break;
    case 3:
      color = CRGB::Yellow;
      couleur = "jaune";
      splash(color);
      break;
    case 4:
      couleur = "arc-en-ciel";
      FastLED.clear(); 
      rainbowWithGlitter();
      break;
    
    default:
      color = CRGB::White; // Default color if no valid choice is given
      couleur = "défaut(arc-en-ciel)";
      splash(color);
      break;
    }
  return couleur;
}


void splash(CRGB color) {
  for (uint8_t size = 2; size <= MATRIX_WIDTH; size += 2) { // Increase size by 2 each iteration
    int centerX = MATRIX_WIDTH / 2;
    int centerY = MATRIX_HEIGHT / 2;
    int startX = centerX - size / 2;
    int startY = centerY - size / 2;
    int endX = startX + size;
    int endY = startY + size;

    for (int x = startX; x < endX; ++x) {
      for (int y = startY; y < endY; ++y) {
        if (x >= 0 && x < MATRIX_WIDTH && y >= 0 && y < MATRIX_HEIGHT) {
          leds[XY(x, y)] = color;
        }
      }
    }
    FastLED.show();
    delay(20); // Delay to visualize the growth of the square
    FastLED.clear(); // Clear the matrix before drawing a larger square
  }
}

uint16_t XY(uint8_t x, uint8_t y) {
  uint16_t i;
  if (y % 2 == 0) {
    // Even rows run forward
    i = (y * MATRIX_WIDTH) + x;
  } else {
    // Odd rows run backward
    i = (y * MATRIX_WIDTH) + (MATRIX_WIDTH - 1 - x);
  }
  return i;
}


void setup() {
  // put your setup code here, to run once:
  // Initialiser le M5Stack
  M5.begin();
  //M5.Power.begin();
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
  FastLED.setBrightness(50); // Luminosité initiale (0-255)

  // Afficher une séquence d'initialisation
  /*for (int i = 0; i < NUM_LEDS; i++) {
    leds[i] = CRGB::Red;
    FastLED.show();
    delay(50);
    leds[i] = CRGB::Black;
  }*/

}

void loop() {
  // Lire les boutons
  M5.update();
  // put your main code here, to run repeatedly:
  // Changer de mode avec le bouton A
  if (M5.BtnA.wasPressed()) {
    mode = (mode + 1) % 5; // 5 modes disponibles
    M5.Lcd.fillRect(0, 100, 320, 20, BLACK);
    M5.Lcd.setCursor(0, 100);
    M5.Lcd.print("Mode: ");
    String couleur = choixCouleur(mode);
    M5.Lcd.print(couleur);
  }
    // Augmenter la luminosité avec le bouton B
  if (M5.BtnB.wasPressed()) {
    uint8_t brightness = FastLED.getBrightness();
    brightness = brightness + 25 > 255 ? 255 : brightness + 25;
    FastLED.setBrightness(brightness);
    M5.Lcd.fillRect(0, 120, 320, 20, BLACK);
    M5.Lcd.setCursor(0, 120);
    M5.Lcd.print("Luminosite: ");
    M5.Lcd.print(brightness);
  }
  
  // Diminuer la luminosité avec le bouton C
  if (M5.BtnC.wasPressed()) {
    uint8_t brightness = FastLED.getBrightness();
    brightness = brightness - 25 < 0 ? 0 : brightness - 25;
    FastLED.setBrightness(brightness);
    M5.Lcd.fillRect(0, 120, 320, 20, BLACK);
    M5.Lcd.setCursor(0, 120);
    M5.Lcd.print("Luminosite: ");
    M5.Lcd.print(brightness);
  }

}
