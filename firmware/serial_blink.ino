void setup() {
  Serial.begin(9600);
  pinMode(13, OUTPUT);
  Serial.println("SERIAL_BLINK_READY_9600");
}

void loop() {
  digitalWrite(13, HIGH);
  Serial.println("HEARTBEAT:HIGH");
  delay(1000);
  digitalWrite(13, LOW);
  Serial.println("HEARTBEAT:LOW");
  delay(1000);
}
