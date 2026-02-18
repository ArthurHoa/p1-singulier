#include <SPI.h>
#include <SD.h>
#include <MFRC522.h>
#include <WiFiNINA.h>
#include <NTPClient.h>
#include <ArduinoRS485.h>
#include <ArduinoModbus.h>

#include "config.h"

// RFID
#define SS_PIN 7
#define RST_PIN 6

// SD write
const int chipSelect = 4;
const char* ntpServer = "0.fr.pool.ntp.org"; 

int status = WL_IDLE_STATUS;     // the Wifi radio's status
WiFiServer server(8080);
WiFiClient client = server.available();

WiFiUDP udp;
NTPClient timeClient(udp, ntpServer, 3600);

MFRC522 rfid(SS_PIN, RST_PIN);

unsigned long tags[NB_CASIERS] = {0};
unsigned long tags_secondaires[NB_CASIERS] = {0};

// ARDUINO SETUP
void setup() {
  Serial.begin(9600);

  // RFID & MODBUS
  // start the Modbus RTU client in 8N1 mode
  if (!ModbusRTUClient.begin(9600, SERIAL_8N1)) {
    Serial.println("Failed to start Modbus RTU Client!");
  }
  ModbusRTUClient.setTimeout(2 * 1000UL); /* 2 seconds. */
  Serial.println("\nTap RFID/NFC Tag on reader");
	SPI.begin();			// Init SPI bus
	rfid.PCD_Init();	// Init MFRC522

  // WIFI
  enable_WiFi();
  connect_WiFi();
  server.begin();

  // Initialisation de la carte SD
  if (!SD.begin(chipSelect)) {
    Serial.println("Échec de l'initialisation de la carte SD !");
    return;
  }

  // Init client NTP
  timeClient.begin();

  // LOAD USERS
  loadUsers();
}


// OPEN DOOR
void open_door(int i) {
    if ((i >= 0)&&(i<NB_CASIERS)) {
      // Serial.println(i);
      if (!ModbusRTUClient.coilWrite(1,i,0xFF)) {
       Serial.print("Failed to write coil! ");
       Serial.println(ModbusRTUClient.lastError());
      }
      delay(200);
      if(!ModbusRTUClient.coilWrite(1,i,0x00)) {
       Serial.print("Failed to write coil! ");
       Serial.println(ModbusRTUClient.lastError());
      }
    }
}

// CHECK CARD
void card_check(unsigned long key) {
  if (key == MASTER_KEY) {
    Serial.print("MASTER_KEY\n");
    for (int i = 0; i < NB_CASIERS; i++) {
      open_door(i);
    }
  }
  for (int i = 0; i < NB_CASIERS; i++) {
    if((key == tags[i]) || (key == tags_secondaires[i])) {
      Serial.print("key\n");
      open_door(i);
    }
  }

  // Enregistrer le log
  log_card(key);
}

// LOG CARD
void log_card(unsigned long key) {
  long maxFileSize = 3000; // Taille max fichier

  // Vérifier si le fichier existe
  if (SD.exists("datalog.txt")) {
    File dataFile = SD.open("datalog.txt", FILE_READ);
    // Vérifier la taille du fichier
    long fileSize = dataFile.size();
    // Fermer le fichier avant toute suppression ou réécriture

    dataFile.close();

    // Si la taille dépasse 1 Mo, on supprime le fichier
    if (fileSize > maxFileSize) {
      SD.remove("datalog.txt");
      Serial.println("Suppression des logs.");
    }
  }

  // Mettre à jour l'heure NTP
    timeClient.update();

    // Construire le timestamp HH:MM:SS sans String
    int h = timeClient.getHours();
    int m = timeClient.getMinutes();
    int s = timeClient.getSeconds();

    char timestamp[9]; // "HH:MM:SS" + '\0'
    sprintf(timestamp, "%02d:%02d:%02d", h, m, s);

    // Construire la ligne complète
    char line[32];
    sprintf(line, "%lu;%s", key, timestamp);

  File dataFile = SD.open("datalog.txt", FILE_WRITE);
  if (dataFile) {
    // Ajouter la ligne passée en paramètre
    dataFile.println(line);
    dataFile.close();  // Fermer le fichier après écriture
  }
}

// READ LOGS
String read_logs() {
  String fileContent = "";

  // Vérifier si le fichier existe
  if (SD.exists("datalog.txt")) {
    File dataFile = SD.open("datalog.txt", FILE_READ);
    // Vérifier si le fichier s'est bien ouvert
    if (dataFile) {
      // Lire le fichier caractère par caractère et ajouter dans fileContent
      while (dataFile.available()) {
        fileContent += (char)dataFile.read();
      }

      dataFile.close();  // Fermer le fichier après la lecture
    }
  }

  return fileContent;
}

// REMOVE LOGS
void remove_logs() {
  // Vérifier si le fichier existe
  if (SD.exists("datalog.txt")) {
    SD.remove("datalog.txt");
  }
}

// SAVE USERS
void saveUsers() {
  if (SD.exists("tags.txt"))
    SD.remove("tags.txt");
  if (SD.exists("tags_sup.txt"))
    SD.remove("tags_sup.txt");

  File dataFile = SD.open("tags.txt", FILE_WRITE);
  if (dataFile) {
    for (int i = 0; i < sizeof(tags) / sizeof(tags[0]); i++) {
      dataFile.println(tags[i]);
    }
    dataFile.close();
  } else
    Serial.println("Erreur lors de l'ouverture du fichier.");

  dataFile = SD.open("tags_sup.txt", FILE_WRITE);
  if (dataFile) {
    for (int i = 0; i < sizeof(tags_secondaires) / sizeof(tags_secondaires[0]); i++) {
      dataFile.println(tags_secondaires[i]);
    }
    dataFile.close();
  } else
    Serial.println("Erreur lors de l'ouverture du fichier.");
}

// LOAD USERS
void loadUsers() {
  File dataFile = SD.open("tags.txt");
  if (dataFile) {
    int index = 0;
    while (dataFile.available() && index < NB_CASIERS) {
      tags[index++] = dataFile.parseInt();
    }
    dataFile.close();
  }

  dataFile = SD.open("tags_sup.txt");
  if (dataFile) {
    int index = 0;
    while (dataFile.available() && index < NB_CASIERS) {
      tags_secondaires[index++] = dataFile.parseInt();
    }
    dataFile.close();
  }
}

// WIFI SETUP
void enable_WiFi() {
  // check for the WiFi module:
  if (WiFi.status() == WL_NO_MODULE) {
    Serial.println("Communication with WiFi module failed!");
    while (true);
  }
  String fv = WiFi.firmwareVersion();
  if (fv < "1.0.0") {
    Serial.println("Please upgrade the firmware");
  }
}

// CONNECT TO WIFI
void connect_WiFi() {
  // attempt to connect to Wifi network:
  while (status != WL_CONNECTED) {
    Serial.println("Attempting to connect to SSID");
    // Connect to WPA/WPA2 network. Change this line if using open or WEP network:
    status = WiFi.begin(WIFI_SSID, WIFI_PASS);

    // wait 5 seconds for connection:
    delay(5000);
  }
}

// READ WIFI MESSAGE
void readClient() {
  if (client) {                             // if you get a client,
    Serial.println("new client");           // print a message out the serial port
    while (client.connected()) {            // loop while the client's connected
      if (client.available()) {             // if there's bytes to read from the client,
        char c = client.read();             // read a byte, then
        if (c == '.') {                    // if the byte is a newline character
            client.println("OK");
            break;
        }
        else if (c != '\r') {
          if (c == 'l') { // send LOGS
            client.println(read_logs());
          }
          else if (c == 'r') { // remove LOGS
            remove_logs();
          }   
          else if (c == 'a') { // open ALL
            for (int i = 0; i < NB_CASIERS; i++) {
              open_door(i);
            }
          }
          else if (c == 'c') { // load CASIERS
            c = client.read();
            for (int i = 0; i < NB_CASIERS; i++) { // Refresh casiers
              tags_secondaires[i] = 0;
              tags[i] = 0;
            }
            int nbcasier = 0;
            while (c == '-' || c == ',') {
              bool casier_secondaire = false;
              if (c == ',')
                casier_secondaire = true;

              char key[9];
              for(int i = 0; i < 8; i++) {
                c = client.read();
                key[i] = c;
              }
              key[8] = '\0';
              unsigned long value = strtoul(key, NULL, 16);
              
              if (casier_secondaire)
                tags_secondaires[nbcasier-1] = value;
              else{
                tags[nbcasier] = value;
                nbcasier++;
              }
              c = client.read();
            }
            saveUsers(); // save on SD
            break;
          } else if (c == 'o'){ // OPEN casier
            char order[4]; // max 3 chiffres casier + '\0'
            int i = 0;
            while (c != '.' && i < 3) {
                c = client.read();
                order[i++] = c;
            }
            order[i] = '\0';
            open_door(atoi(order));
            break;
          }
        }
      }
    }
    // close the connection:
    client.stop();
    Serial.println("client disconnected");
  }
}

// MAIN LOOP
void loop() {
  unsigned long carte;
  if (rfid.PICC_IsNewCardPresent()) { // new tag is available
    if (rfid.PICC_ReadCardSerial()) { // NUID has been readed
      MFRC522::PICC_Type piccType = rfid.PICC_GetType(rfid.uid.sak);

      // Read card 
      carte =  (unsigned long)rfid.uid.uidByte[0] << 24;
      carte += (unsigned long)rfid.uid.uidByte[1] << 16;
      carte += (unsigned long)rfid.uid.uidByte[2] <<  8;
      carte += (unsigned long)rfid.uid.uidByte[3];
      Serial.print("key UID: ");
      Serial.print(carte);
      Serial.println();
      // Card check
      card_check(carte);

      // End
      rfid.PICC_HaltA(); // halt PICC
      rfid.PCD_StopCrypto1(); // stop encryption on PCD
    }
  }

  client = server.available();

  if (client) {
    readClient();
  }
}

