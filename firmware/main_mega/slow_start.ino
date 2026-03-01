void setup() {
  delay(5000);
  Serial.begin(115200);
  delay(1000);
  Serial.println("I_AM_ALIVE");
}

void loop() {
  Serial.println("LOOPING");
  delay(1000);
}
