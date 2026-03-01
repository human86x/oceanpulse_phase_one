void setup() {
  Serial.begin(115200);
  Serial.println("MINIMAL_READY");
}

void loop() {
  Serial.println("ALIVE");
  delay(1000);
}
