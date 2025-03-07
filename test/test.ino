
/*
   Contrôle d'une matrice RGB 16*16
 
   Plus d'infos:
   http://electroniqueamateur.blogspot.com/2020/06/matrice-de-leds-rgb-16-x-16-ws2812b-et.html
 
 */

#include <FastLED.h>        //https://github.com/FastLED/FastLED
#include <LEDMatrix.h>      //https://github.com/Jorgen-VikingGod/LEDMatrix
#include <M5Core2.h>

#define DATA_PIN            33
#define COLOR_ORDER         GRB
#define CHIPSET             WS2812B

// initial matrix layout (to get led strip index by x/y)
#define MATRIX_WIDTH        16
#define MATRIX_HEIGHT       16
#define MATRIX_TYPE         HORIZONTAL_ZIGZAG_MATRIX
#define MATRIX_SIZE         (MATRIX_WIDTH*MATRIX_HEIGHT)
#define NUMPIXELS           MATRIX_SIZE

cLEDMatrix<MATRIX_WIDTH, MATRIX_HEIGHT, MATRIX_TYPE> leds;

#define pause 300

void setup()
{
  FastLED.addLeds<CHIPSET, DATA_PIN, COLOR_ORDER>(leds[0], leds.Size()).setCorrection(TypicalSMD5050);
  FastLED.setCorrection(TypicalLEDStrip);
  FastLED.setBrightness(50);
  FastLED.clear(true);  // on éteint toutes les LEDs

}


void loop()
{

  // ----- Allumer une LED en particulier ------------------------------

  leds.DrawPixel(3, 3, (CRGB::Green));
  FastLED.show();
  delay(pause);
  leds.DrawPixel(3, 4, (CRGB::Blue));
  FastLED.show();
  delay(pause);
  leds.DrawPixel(4, 3, (CRGB::Red));
  FastLED.show();
  delay(pause);
  leds.DrawPixel(4, 4, (CRGB::Yellow));
  FastLED.show();
  delay(pause);

  // effet miroir: on reproduit le même motif dans les 3 autres quadrants

  leds.QuadrantMirror();
  FastLED.show();
  delay(2 * pause);

  // ----- Déplacer le motif vers la droite --------------------------

  for (int i = 0; i <= 12; i++) {
    leds.ShiftRight();
    FastLED.show();
    delay(pause / 2);
  }

  // ------ dessiner une ligne droite -------------------------------

  leds.DrawLine(4, 0, 4, 255, (CRGB::Green));
  FastLED.show();
  delay(pause);
  leds.DrawLine(11, 0, 11, 255, (CRGB::Blue));
  FastLED.show();
  delay(pause);
  leds.DrawLine(0, 4, 255, 4, (CRGB::Red));
  FastLED.show();
  delay(pause);
  leds.DrawLine(0, 11, 255, 11, (CRGB::Pink));
  FastLED.show();
  delay(pause);


  // effet miroir ------------------------------------

  leds.QuadrantTopTriangleMirror();
  FastLED.show();
  delay(2 * pause);

  FastLED.clear(true);  // on éteint toutes les LEDs

  // dessiner un carré (vide) ---------------------------

  leds.DrawRectangle(6, 6, 9, 9, (CRGB::Red));
  FastLED.show();
  delay(pause);
  leds.DrawRectangle(5, 5, 10, 10, (CRGB::Yellow));
  FastLED.show();
  delay(pause);
  leds.DrawRectangle(4, 4, 11, 11, (CRGB::Lime));
  FastLED.show();
  delay(pause);
  leds.DrawRectangle(3, 3, 12, 12, (CRGB::Cyan));
  FastLED.show();
  delay(pause);

  FastLED.clear(true);  // on éteint toutes les LEDs

  // -- dessiner un cercle plein ------------------------

  leds.DrawFilledCircle(4, 4, 2, (CRGB::Blue));
  FastLED.show();
  delay(pause);

  // -- miroir horizontal -------------------------
  leds.HorizontalMirror();
  FastLED.show();
  delay(pause);

  // -- miroir vertical --------------------------
  leds.VerticalMirror();
  FastLED.show();
  delay(pause);

  FastLED.clear(true);  // on éteint toutes les LEDs

}