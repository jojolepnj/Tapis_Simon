#include <SPI.h>
#include <WiFi.h>
#include <DFRobot_PN532.h>

#define block (5)
#define PN532_IRQ (2)
#define INTERRUPT (1)
#define POLLING (0)

char ssid[] = "Simon";
char password[] = "Simon1234";

int status = WL_IDLE_STATUS;

byte mac[6];
DFRobot_PN532_IIC nfc(PN532_IRQ, POLLING);
DFRobot_PN532::sCard_t NFCcard;

void setup() {
    Serial.begin(115200);

    status = WiFi.begin(ssid, password);

    if (status != WL_CONNECTED) {
        Serial.println("Couldn't get a wifi connection");
        while (true);
    } else {
        WiFi.macAddress(mac);
        Serial.print("MAC: ");
        Serial.print(mac[5], HEX);
        Serial.print(":");
        Serial.print(mac[4], HEX);
        Serial.print(":");
        Serial.print(mac[3], HEX);
        Serial.print(":");
        Serial.print(mac[2], HEX);
        Serial.print(":");
        Serial.print(mac[1], HEX);
        Serial.print(":");
        Serial.println(mac[0], HEX);
    }

    while (!nfc.begin()) {
        Serial.println("initial failure");
        delay (1000);
    }
    Serial.println("Waiting for a card......");
}

void loop() {
    uint8_t dataWrite[4] = {2, 0, 1, 9};
    uint8_t dataRead[4];

    if (nfc.scan()) {
        NFCcard = nfc.getInformation();
        if (NFCcard.AQTA[1] == 0x44 && memcmp(NFCcard.cardType, "Ultralight", 10) != 0) {
            Serial.print("Data to be written(HEX):");
            for (int i = 0; i < 4; i++) {
                Serial.print(dataWrite[i], HEX);
                Serial.print(" ");
            }
            Serial.println("");
            Serial.print("The execution result:");
            if (nfc.writeNTAG(block, dataWrite) == 1) {
                Serial.println("write success");
            } else {
                Serial.println("write failure");
            }
            Serial.print("Data read(HEX):");
            if (nfc.readNTAG(dataRead, block) == 1) {
                Serial.print(":");
                for (int i = 0; i < 4; i++) {
                    Serial.print(dataRead[i], HEX);
                    Serial.print(" ");
                }
                Serial.println("");
            } else {
                Serial.println("Read failure");
            }
        } else {
            Serial.println("The card type is not NTAG21x...");
        }
    }
    delay(2000);
}