void setup() {
  Serial.begin(115200);
}

void loop() {
  Serial.write('A');
  delay(100);
}
