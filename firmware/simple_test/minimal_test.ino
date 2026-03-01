void setup() {
  Serial.begin(115200);
  while(!Serial);
  Serial.println("SETUP_DONE");
}

void loop() {
  Serial.println("LOOP");
  delay(5000);
}
