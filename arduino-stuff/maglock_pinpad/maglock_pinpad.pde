/* 
 * Modified by myddrn to drive a maglock with an RFID reader
 * 
 * Crazy People
 * By Mike Cook April 2009
 * Three RFID readers outputing 26 bit Wiegand code to pins:-
 * Reader A (Head) Pins 2 & 3
 * Interrupt service routine gathers Wiegand pulses (zero or one) until 26 have been recieved
 * Then a sting is sent to processing
 */

volatile long reader1 = 0;
volatile int reader1Count = 0;

int DATA_0 = 2;
int DATA_1 = 3;
int GREEN_LED = 4;
int RED_LED = 5;

int READING_DATA_FLAG = 0;
int DONE_READING_FLAG = 0;
int READ_ERROR = 0;



unsigned long TIMER_CONST = 0;
unsigned long TIMER_CURRENT = 0;

void reader1One(void)
{
  //Serial.println("READONE");
  READING_DATA_FLAG = 1;
  TIMER_CONST = millis();
  reader1Count++;
  reader1 = reader1 << 1;
  reader1 |= 1;
}

void reader1Zero(void)
{
  //Serial.println("READZERO");
  READING_DATA_FLAG = 1;
  TIMER_CONST = millis();
  reader1Count++;
  reader1 = reader1 << 1;
}

void setup()
{
  Serial.begin(9600);
  pinMode(13,OUTPUT);
  // Attach pin change interrupt service routines from the Wiegand RFID readers
  attachInterrupt(1, reader1Zero, RISING);//DATA0 to pin 2
  attachInterrupt(0, reader1One, RISING); //DATA1 to pin 3
  delay(10);
  // the interrupt in the Atmel processor mises out the first negitave pulse as the inputs are already high,
  // so this gives a pulse to each reader input line to get the interrupts working properly.
  // Then clear out the reader variables.
  // The readers are open collector sitting normally at a one so this is OK
  for(int i = 2; i < 4; i++)
  {
    pinMode(i, OUTPUT);
    digitalWrite(i, HIGH); // enable internal pull up causing a one
    digitalWrite(i, LOW); // disable internal pull up causing zero and thus an interrupt
    pinMode(i, INPUT);
    digitalWrite(i, HIGH); // enable internal pull up
  }
  delay(10);
  //pinMode(GREEN_LED, OUTPUT);
  //pinMode(RED_LED, OUTPUT);
  //digitalWrite(GREEN_LED,LOW);
  //digitalWrite(RED_LED,LOW);
  // put the reader input variables to zero
  reader1 = 0;
  reader1Count = 0;
  //digitalWrite(13, HIGH);  // show Arduino has finished initilisation
}

void loop()
{
  
  TIMER_CURRENT = millis();

  if(reader1Count >= 1)
  {
    if (READING_DATA_FLAG == 1)
    {
      int time_diff = TIMER_CURRENT - TIMER_CONST;
      
      if (time_diff > 20)
      {
        //Serial.println(reader1,BIN);
        
        DONE_READING_FLAG = 1;
      }
      
    }
    
    //Serial.print(" Reader 1 ");
    
    //Send the value we read from the RFID reader down the serial line
  }
  else
  {
    //Serial.println("HEARTBEAT");
  }
  
  if(DONE_READING_FLAG == 1)
  {
    DONE_READING_FLAG = 0;
    READING_DATA_FLAG = 0;
    if (reader1Count == 4)
    {
      Serial.print("KEY:");
      Serial.println(reader1& 0xfffffff);
    }
    else if (reader1Count == 26)
    {
      Serial.print("26CARD:");
      Serial.println(reader1& 0xfffffff);
    }
    else
    {
      //digitalWrite(GREEN_LED,HIGH);
      //digitalWrite(RED_LED,HIGH);
      //delay(100);
      //digitalWrite(GREEN_LED,LOW);
      //digitalWrite(RED_LED,LOW);
      READ_ERROR = 1;
      //Serial.print(reader1Count);
      //Serial.print("CARD:");
      //Serial.println(reader1& 0xfffffff);
    }
    

    //Reset all the stuff that handles reading in the RFID reader info
    reader1 = 0;
    reader1Count = 0;
    
    if ( READ_ERROR == 0 )
    {
    
      char val = 0;
      
      
      //Wait for 100 millis before checking for a response from the serial line
      delay(100);
      
      String incoming = "";
  
      //This part manages the reading of data back from whatever is checking the RFID card values
      if (Serial.available())
      {
  
        //We have to read in the serial byte by byte from the buffer
        val = Serial.read();
        
        while (val != -1)
        {
          incoming += String(val);
          delay(10);
          val = Serial.read();
        }
      }
      //Serial.print("INCOMING=");
      //Serial.println(incoming);
      
      //This part powers the relay and opens the lock
      if (incoming == "OPEN")
      {
        //Serial.println("OPENDED");
        digitalWrite(13,HIGH);
        delay(2500);
        digitalWrite(13,LOW);
      }
    
    }
    else
    {
      READ_ERROR = 0;
    }

  }
}
