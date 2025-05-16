#include <unity.h>
#include <WiFi.h>

// Mock du statut WiFi
int mockedStatus = WL_IDLE_STATUS;
int WiFi_begin_calls = 0;

wl_status_t WiFiClass::status() {
    // Après 3 appels, on simule la connexion
    WiFi_begin_calls++;
    if (WiFi_begin_calls >= 3) return WL_CONNECTED;
    return WL_DISCONNECTED;
}

void test_WiFiConnectStopsWhenConnected() {
    WiFi_begin_calls = 0;
    // Appel de la logique de connexion (copie simplifiée)
    uint32_t start = millis();
    while (WiFi.status() != WL_CONNECTED) {
        delay(1);
        // on limite pour éviter boucle infinie
        if (millis() - start > 10) {
            TEST_FAIL_MESSAGE("La connexion WiFi n'est pas arrivée à WL_CONNECTED en temps voulu");
            return;
        }
    }
    // On s'attend à être sortis de la boucle avant 10 ms
    TEST_ASSERT_LESS_THAN_UINT32(10, WiFi_begin_calls);
}

void setup() {
    UNITY_BEGIN();
    RUN_TEST(test_WiFiConnectStopsWhenConnected);
    UNITY_END();
}

void loop() {}
