#include <unity.h>
#include <cstring>

void test_UIDConversionToHexString() {
    uint8_t uid[] = {0x02, 0xAB, 0x3F, 0x00};
    int uidLength = 4;
    char tagID[uidLength * 2 + 1];
    memset(tagID, 0, sizeof(tagID));

    for (int i = 0; i < uidLength; i++) {
        sprintf(tagID + i * 2, "%02X", uid[i]);
    }

    // Chaîne attendue : "02AB3F00"
    TEST_ASSERT_EQUAL_STRING("02AB3F00", tagID);
}

void setup() {
    UNITY_BEGIN();
    RUN_TEST(test_UIDConversionToHexString);
    UNITY_END();
}

void loop() {}
