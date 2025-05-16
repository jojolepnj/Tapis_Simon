#include <unity.h>
#include <string>

class MockClient {
  public:
    std::string buffer;
    bool connect(const char*, int) { return true; }
    void print(const char* s) { buffer += s; }
    void print(const std::string& s) { buffer += s; }
    std::string str() const { return buffer; }
    void stop() {}
};

void test_HTTPPostFormatting() {
    const char* serverName = "192.168.1.104";
    const int serverPort = 80;
    const char* path = "/add_passage.php";
    const char* tagID = "02AB3F00";
    char postData[32];
    snprintf(postData, sizeof(postData), "tag=%s", tagID);
    size_t contentLength = strlen(postData);

    MockClient client;
    bool ok = client.connect(serverName, serverPort);
    TEST_ASSERT_TRUE(ok);

    client.print("POST ");
    client.print(path);
    client.print(" HTTP/1.1\r\n");
    client.print("Host: ");
    client.print(serverName);
    client.print("\r\n");
    client.print("Connection: close\r\n");
    client.print("Content-Type: application/x-www-form-urlencoded\r\n");
    client.print("Content-Length: ");
    client.print(std::to_string(contentLength));
    client.print("\r\n\r\n");
    client.print(postData);

    std::string req = client.str();
    // Vérifications clés
    TEST_ASSERT_NOT_NULL(strstr(req.c_str(), "POST /add_passage.php HTTP/1.1\r\n"));
    TEST_ASSERT_NOT_NULL(strstr(req.c_str(), "Host: 192.168.1.104\r\n"));
    TEST_ASSERT_NOT_NULL(strstr(req.c_str(), "\r\n\r\ntag=02AB3F00"));
    TEST_ASSERT_EQUAL_INT((int)contentLength, 9); // "tag=02AB3F00" fait 9 chars
}

void setup() {
    UNITY_BEGIN();
    RUN_TEST(test_HTTPPostFormatting);
    UNITY_END();
}

void loop() {}
