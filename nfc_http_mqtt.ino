#include <SPI.h>
#include <WiFiS3.h>
#include <DFRobot_PN532.h>
#include <PubSubClient.h>

// NFC Configuration
#define PN532_IRQ 2
#define POLLING 0

// WiFi, MQTT and HTTP Configuration
const char* ssid = "Simon";
const char* password = "Simon1234";

// MQTT Configuration
const char* mqtt_server = "192.168.1.106";  
const int mqtt_port = 1883;                 
const char* mqtt_topic_tag = "nfc/tags";     // Topic for tag IDs
const char* mqtt_topic_start = "site/start"; // Topic for site start event

// HTTP Configuration
const char* http_server = "192.168.1.106";
const int http_port = 80;
const char* http_path = "/add_passage.php";

// Initialize objects
DFRobot_PN532_IIC nfc(PN532_IRQ, POLLING);
DFRobot_PN532::sCard_t NFCcard;
WiFiClient espClient;
WiFiClient httpClient;
PubSubClient mqttClient(espClient);

void setup_wifi() {
  delay(10);
  Serial.println("Connecting to WiFi...");
  
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected! IP: " + WiFi.localIP().toString());
}

void reconnect_mqtt() {
  while (!mqttClient.connected()) {
    Serial.println("Attempting MQTT connection...");
    String clientId = "ArduinoNFC-";
    clientId += String(random(0xffff), HEX);
    
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("Connected to MQTT broker");
    } else {
      Serial.print("Failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" Retrying in 5 seconds...");
      delay(5000);
    }
  }
}

void sendHttpPost(const char* tagId) {
  if (httpClient.connect(http_server, http_port)) {
    char postData[50];
    snprintf(postData, sizeof(postData), "tag=%s", tagId);
    size_t contentLength = strlen(postData);

    httpClient.print("POST ");
    httpClient.print(http_path);
    httpClient.print(" HTTP/1.1\r\n");
    httpClient.print("Host: ");
    httpClient.print(http_server);
    httpClient.print("\r\n");
    httpClient.print("Connection: close\r\n");
    httpClient.print("Content-Type: application/x-www-form-urlencoded\r\n");
    httpClient.print("Content-Length: ");
    httpClient.print(contentLength);
    httpClient.print("\r\n\r\n");
    httpClient.print(postData);

    Serial.println("Sent HTTP POST data: " + String(postData));

    while (httpClient.connected() || httpClient.available()) {
      if (httpClient.available()) {
        String line = httpClient.readStringUntil('\n');
        Serial.println(line);
      }
    }
    httpClient.stop();
  } else {
    Serial.println("HTTP Connection failed!");
  }
}

void setup() {
  Serial.begin(115200);
  
  // Connect to WiFi
  setup_wifi();
  
  // Configure MQTT
  mqttClient.setServer(mqtt_server, mqtt_port);
  
  // Initialize NFC
  while (!nfc.begin()) {
    Serial.println("NFC init failed. Retrying...");
    delay(1000);
  }
  Serial.println("NFC initialized - Scan an NFC tag...");
}

void loop() {
  // Ensure MQTT connection
  if (!mqttClient.connected()) {
    reconnect_mqtt();
  }
  mqttClient.loop();

  if (WiFi.status() == WL_CONNECTED) {
    // Try to read NFC tag
    if (nfc.scan()) {
      NFCcard = nfc.getInformation();
      char tagID[NFCcard.uidlenght * 2 + 1];
      
      // Convert UID bytes to hex string
      for (int i = 0; i < NFCcard.uidlenght; i++) {
        sprintf(tagID + i * 2, "%02X", NFCcard.uid[i]);
      }
      Serial.print("Scanned Tag ID: ");
      Serial.println(tagID);

      // Publish to MQTT topics
      mqttClient.publish(mqtt_topic_tag, tagID);     // Publish tag ID
      mqttClient.publish(mqtt_topic_start, "1");     // Publish site start event

      // Send data via HTTP POST
      sendHttpPost(tagID);
      
      delay(2000); // Wait after scan
    }
  } else {
    Serial.println("WiFi disconnected. Reconnecting...");
    setup_wifi();
  }
  
  delay(100); // Small delay
}