void setup() {
  // Set baud rate to 115200 for 16MHz clock
  UBRR0H = 0;
  UBRR0L = 16; // 115200 at 16MHz
  UCSR0B = (1 << TXEN0); // Enable TX
  UCSR0C = (1 << UCSZ01) | (1 << UCSZ00); // 8N1
}

void loop() {
  while (!(UCSR0A & (1 << UDRE0))); // Wait for empty transmit buffer
  UDR0 = 'A';
  delay(1000);
}
