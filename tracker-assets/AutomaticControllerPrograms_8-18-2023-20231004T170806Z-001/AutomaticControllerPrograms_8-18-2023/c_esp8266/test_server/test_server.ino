#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h>
#include <WiFiClient.h>

// OUR SERVER'S PORT, 80 FOR DEFAULT
WiFiServer server(80);
WiFiClient client;
String rule;

// Set your Static IP address
// Set your Gateway IP address
//EROB//IPAddress local_IP(192, 168, 1, 184);
//EROB//IPAddress gateway(192, 168, 1, 1);
IPAddress local_IP(10, 1, 10, 58);//SOLERA//
IPAddress gateway(10, 1, 10, 1);//SOLERA//


IPAddress subnet(255, 255, 0, 0);
IPAddress primaryDNS(8, 8, 8, 8);   //optional
IPAddress secondaryDNS(8, 8, 4, 4); //optional

void start(String ssid, String pass)
{
    // Configures static IP address
  if (!WiFi.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS)) {
    Serial.println("STA Failed to configure");
  }

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid.c_str(),pass.c_str());

  Serial.println("");
// Wait for connection
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.println(".");
  }
  Serial.println("");
  Serial.print("Connected to ");
  Serial.println(ssid);
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
  if (!MDNS.begin("esp8266")) {
    Serial.println("Error setting up MDNS responder!");
    while (1) {
      delay(1000);
    }
  }
  Serial.println("mDNS responder started");
  server.begin();
  Serial.println("TCP server started");
  MDNS.addService("http", "tcp", 80);
}

bool CheckNewReq(){
  client = server.available();
  if (!client) {
    return 0;
  }
  static char incoming[100];
  int index = 0;
  for(index=0;index<50;index++) incoming[index] = '\0';
  client.readBytesUntil('\n', incoming, 100);
  int addr_start = 0;
  int addr_end = 0;
  for(index=0;index<50;index++) {
    if(incoming[index]==' ' && addr_start==0) addr_start = index+1;
    else if(incoming[index]==' ' && addr_start>0 && addr_end==0) addr_end = index;
  }
  if (addr_start == 0 || addr_end == 0) {
    Serial.print("Invalid request:");
    Serial.println(incoming);
    return 0;
  }
  char req[50];
  for(index=addr_start;index<addr_end;index++) req[index-addr_start] = incoming[index];
  req[index-addr_start] = '\0';
  rule = String(req); 
  
  client.flush();
  return 1;
}

void returnThisStr(String final_data){
  String s;
  client.print(final_data);
}

String getPath(){
  return rule;
}

int pwm = 255;
String path = "nothing";
void setup(){
  char creds = 0;
  char creds_state = 0;
  int byte;
  String STASSID_;
  String STAPSK_;
  Serial.begin(115200);
  Serial.setTimeout(200);

  Serial.write("getting wifi credentials");

  while(!creds)
  {
    switch(creds_state)
    {
      case 0:
        Serial.write("i");
        delay(500);
        if(Serial.available()) creds_state++;
      break;
      case 1:
        byte = Serial.read();
        if(char(byte)=='c') 
        {
          delay(500);
          STASSID_ = Serial.readString();
          delay(200);
          creds_state++;
        }
      break;
      case 2:
        Serial.write("p");
        delay(500);
        if(Serial.available()) creds_state++;
      break;
      case 3:
        byte = Serial.read();
        if(char(byte)=='c') 
        {
          delay(500);
          STAPSK_ = Serial.readString();
          creds = 1;
        }
      break;
    }
  }
  STASSID_.replace("\n", "");
  STAPSK_.replace("\n", "");

  start(STASSID_,STAPSK_);  // Wifi details connect to
}

void loop(){
  static char send_data = 0;
  static String reply_string;

  if(CheckNewReq() == 1)
  {
    if(getPath()=="/wf_hb"){ //heartbeat
      returnThisStr("wfm_hb");
    }
    else if(getPath()=="/data") //request for data from arduino
    {
      if(send_data) 
      {
        send_data = 0;
        //make string custom with latest data... can append bunch of data to parse...
        returnThisStr(reply_string);
        reply_string = "";
      }
      else returnThisStr("no_data");
    }
    else        //here we receive data
    {
      path = getPath();
      //returnThisStr("nothing");
      path.remove(0,1);    //Remove slash /
      Serial.println(path); //send data to arduino
    }
  }
  if(Serial.available()>0)
  {
    delay(50);
    reply_string += Serial.readStringUntil('\n');
    Serial.flush();
    send_data = 1;
  }
  
}