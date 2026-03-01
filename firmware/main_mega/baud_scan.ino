void setup() {}
void loop() {
  Serial.begin(9600);
  Serial.println("TEST_9600");
  Serial.flush();
  Serial.end();
  delay(500);
  Serial.begin(57600);
  Serial.println("TEST_57600");
  Serial.flush();
  Serial.end();
  delay(500);
  Serial.begin(115200);
  Serial.println("TEST_115200");
  Serial.flush();
  Serial.end();
  delay(500);
}
