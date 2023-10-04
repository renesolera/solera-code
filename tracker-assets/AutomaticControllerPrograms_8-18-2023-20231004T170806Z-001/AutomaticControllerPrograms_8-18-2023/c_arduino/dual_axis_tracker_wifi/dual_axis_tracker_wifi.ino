/* 
 * Project Title:     Dual Axis Tracker
 * Author:            E. Robertson
 * Creation Date:     03/13/2023
 * 
 * Revision History:
 * Author     Date          Version     Description
 * EAR        03/19/2023    1.0.0       Initial release
 * EAR        03/20/2023    1.1.0       Added heartbeat from paired python script, debug motor control, print measured and target data when 'targeting'
 * EAR        04/06/2023    1.2.0       Replaced AZ measurement with output from motor hall effects. 
 * EAR        04/11/2023    1.2.1       Added AZ angle tracking and means to set the true angle via python script. 
 * EAR        04/11/2023    1.2.2       Fixed bug that only spun motors one way.  
 * EAR        04/13/2023    1.2.3       Fixed bug in tracking program.  
 * EAR        04/13/2023    1.2.4       Updated positioning from python library. HE tracking. 
 * EAR        04/22/2023    1.2.5       Added decimal support for angles, log to txt file, wake function. 
 * EAR        05/01/2023    1.2.6       Updated wake function. 
 * EAR        05/04/2023    1.2.7       Updated functions to check error and change motor direction if overshot target. 
 * EAR        05/11/2023    1.3.0       Updated serial comms.  
 * EAR        06/27/2023    2.0.0       Convert from serial comms to wifi comss. 
 * EAR        07/25/2023    2.0.1       Moved ZE HE pins to 20/21 from 18/19. 
 * EAR        08/02/2023    2.1.0       Modified serial reading from wifi module, baud rate to 115200, changed WIFI_RST pin.  Added WDT.
 * EAR        08/17/2023    2.1.1       Clear rx buffer each time. Add newline char to Serial2 prints. Add timeout to Serial comms, buad rate to 115200 on both UARTS. Init tracking fx. 
 

***********************/

#include "TimerOne.h"       // Avaiable from http://www.arduino.cc/playground/Code/Timer1
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <avr/wdt.h>

#define STASSID "Solora_2.4" //network ID //SOLERA//
#define STAPSK "ABC1234D"  //network password //SOLERA//
//EROB//#define STASSID "DudleyTheDude" //network ID
//EROB//#define STAPSK "roseway111terrace"  //network password
#define WIFI_CONFIG_TIMEOUT (250)

#define USER_SERIAL (1)

#define SYSTEM_TICK 100
#define NUMTICKS_1MS  10
//timing variables
volatile uint32_t systemClk = 0;
volatile uint8_t b1MSCounter = 0;
uint8_t b10MSCounter = 0;
uint8_t b100MSCounter = 0;
uint8_t b1SCounter = 0;
uint8_t b5SCounter = 0;

uint8_t debug_LED = 1;

char ze_monitor;

const uint32_t uart_header = 0x61626162;
enum uart_classes {
  TARGET_UPDATE,
  MENU_INPUT,
  AZ_UPDATE,
  ALT_UPDATE,
  HEARTBEAT,
  DEBUG  
};

enum menuStates{
  main_menu,
  tracking_program,
  store_program,
  wake_program,
  motor_test_program
};
uint8_t menu_state = main_menu;
uint8_t menu_first_time = 1;

int c = 0;
double measured_azimuth, measured_altitude;
double yaw_global = 0;
char roll_direction, pitch_direction;

float longitude = -80.18;
float latitude = 25.76;
double str_ze = 0.0;
double str_az = 0.0;
double target_altitude = -999;
double target_azimuth = -999;

char tracking_program_flag = 0;
char stow_program_flag = 0;
char zero_program_flag = 0;
char wake_test_flag = 0;
char motor_test_flag = 0;
char motor_state = 0;
char motor_state_first_time = 1;

char heartbeat_counter = 0;

#define MOTOR_AZ_DRIVE (9)
#define MOTOR_ZE_DRIVE (11)
#define MOTOR_AZ_DIR (4)
#define MOTOR_ZE_DIR (13)
#define HE_1_AZ  (2)
#define HE_2_AZ  (3)
#define HE_1_ZE  (18)
#define HE_2_ZE  (19)
#define MAX_ALTITUDE_ALLOWABLE  (86.5)
#define PITCH_POLARITY_1  (0)
#define WIFI_RST (5)

//MOTORS HAVE 8pulses per motor revolution, then a 575:1 gear box, then a 62:1 gear box ->285200 pulses per output revolution. (~792 pulses per output degree)
volatile long HE_counter_AZ = 0;
volatile long target_pulse_reached_AZ;
static long local_temp_pulse, local_temp_pulse_ZE;
long target_pulse_count_AZ;
volatile long HE_counter_ZE = 0;
volatile long target_pulse_reached_ZE;
long target_pulse_count_ZE;

#define AZIMUTH_DIRECTION_POSITIVE (1)
#define AZIMUTH_DIRECTION_NEGATIVE (0)
#define ZENITH_DIRECTION_POSITIVE (1)
#define ZENITH_DIRECTION_NEGATIVE (0)

#define TARGET_STOW_AZIMUTH (180)
#define TARGET_STOW_ZENITH (270)
#define TARGET_WAKE_AZIMUTH (180)
#define TARGET_WAKE_ZENITH (0)
#define ALLOWABLE_ERROR (0.1)
#define ALLOWABLE_ERROR_HE (0.1)
#define MOTOR_DRIVE_STRENGTH (255)
#define MOTOR_TIMEOUT (1200) //100ms

#define HEARTBEAT_TIMEOUT_SECONDS (25)

#define PRINT_TIME_COUNTS_100MS (10)//(50) 

void reset_wfi_module(void)
{
  pinMode(WIFI_RST, INPUT); // HIGH IMPEDANCE
  pinMode(WIFI_RST, OUTPUT);
  digitalWrite(WIFI_RST, LOW);
  delay(200);
  pinMode(WIFI_RST, INPUT); // HIGH IMPEDANCE
  delay(200);
}
char configure_wifi_credentials(void)
{
  char creds = 0;
  char creds_state = 0;
  char old_creds_state = 1;
  int byte;
  int reset_timeout = 0;
  char rtn_val = 0;
  char fail_counter;

  while(!creds)
  {
    if(creds_state!=old_creds_state)
    {
      old_creds_state = creds_state;
      Serial.print("creds: ");
      Serial.println(creds_state+30);
    }
    switch(creds_state)
    {
      case 0:
        reset_wfi_module();//Reset WifiModule
        delay(500);
        Serial2.flush();
        reset_timeout = 0;
        creds_state++;
        fail_counter++;
        if(fail_counter>2) 
        {
          rtn_val = 0;
          break;
        }
      break;
      case 1:
        while(!Serial2.available());
        byte = Serial2.read();
        Serial2.flush();
        if(char(byte)=='i') 
        {
          creds_state++;
          Serial2.write("c");
        }
        delay(50);
      break;
      case 2:
        Serial2.write(STASSID);
        delay(200);
        Serial2.flush();
        creds_state++;
      break;
      case 3:
        while(!Serial2.available());
        byte = Serial2.read();
        Serial2.flush();
        if(char(byte)=='p') 
        {
          creds_state++;
          Serial2.write("c");
        }
        delay(50);
      break;
      case 4:
        Serial2.write(STAPSK);
        creds_state++;
      break;
      case 5:
        while(!Serial2.available());
        delay(50);
        String temp_str = Serial2.readString();
        if(temp_str.indexOf("CP server start")>=0) 
        {
          creds = 1;  
          Serial.println("Wifi started.");
          rtn_val = 1;
        }
      break;
    }
    reset_timeout++;
    if(reset_timeout>=WIFI_CONFIG_TIMEOUT) creds_state = 0;
  }

  return rtn_val;
}
void init_menu(void)
{
  menu_state = main_menu;
  menu_first_time = 0;
}

char serial_rx(void)
{
  char ser_vals[50];
  int bytes_read = 0;
  int i;
  char substr[8];
  int x = 0;

  i=0;
  while(i<50)
  {
    ser_vals[i]=0x00;
    i++;
  }
  i=0;
  if (Serial2.available()>0)
  {
    delay(50);
    char buffer[100];
    for(int i=0;i<100;i++) buffer[i] = '\0';
    Serial2.readBytesUntil('\n', buffer, 100);
    //split by commas
    char* token = strtok(buffer, ",");
    int index = 0;
    float degrees1, degrees2;
    int uart_class;
    char received_char;
    double set_target_altitude, set_target_azimuth, set_current_altitude, set_current_azimuth;
    while(token!=NULL)
    {
      if(USER_SERIAL) Serial.println(token);
      if(index==0) 
      {
        uart_class = atoi(token);
        if(USER_SERIAL) Serial.print("class: ");
        if(USER_SERIAL) Serial.println(uart_class);
      }
      else if(index==1)
      {
        if(uart_class==MENU_INPUT)
        {
          received_char = (token[0]);
          if(received_char == 109 && menu_state!=main_menu) 
          {
            menu_state = main_menu;
            menu_first_time = 1;
          }
          if(received_char == 116 && menu_state!=tracking_program) 
          {
            menu_state = tracking_program;
            menu_first_time = 1;
          }
          if(received_char == 115 && menu_state!=store_program) 
          {
            menu_state = store_program;
            menu_first_time = 1;
          }
          if(received_char == 122 && menu_state!=main_menu) 
          {
            menu_state = main_menu;
            menu_first_time = 1;
          }
          if(received_char == 119 && menu_state!=wake_program) 
          {
            menu_state = wake_program;
            menu_first_time = 1;
          }
          if(received_char >= 97 && received_char <= 101)
          {
            menu_state = motor_test_program;
            menu_first_time = 1;
            motor_state = char(received_char)-97;
            motor_state_first_time = 1;
          }
          if(received_char == 104) 
          {
            HE_counter_AZ = 0;
            HE_counter_ZE = 0;
          }
        }
        else if(uart_class==TARGET_UPDATE||uart_class==AZ_UPDATE||uart_class==ALT_UPDATE)
        {
          degrees1 = atof(token);
          if(uart_class==TARGET_UPDATE) 
          {
            set_target_altitude = (degrees1);
            if(set_target_altitude>MAX_ALTITUDE_ALLOWABLE)
            {
              if(USER_SERIAL) Serial.print("altitude target too high, setting to max: ");
              set_target_altitude = MAX_ALTITUDE_ALLOWABLE;
            }
            else if(USER_SERIAL) Serial.print("setting target altitude: ");
            target_altitude = set_target_altitude;
            if(USER_SERIAL) Serial.println(target_altitude, 2);
          }
          if(uart_class==AZ_UPDATE)
          {
            set_current_azimuth = degrees1;
            measured_azimuth = set_current_azimuth;
            if(USER_SERIAL) Serial.print("setting current azimuth: ");
            if(USER_SERIAL) Serial.println(measured_azimuth, 2);
          }
          if(uart_class==ALT_UPDATE)
          {
            set_current_altitude = degrees1;
            measured_altitude = set_current_altitude;
            if(USER_SERIAL) Serial.print("setting current altitude: ");
            if(USER_SERIAL) Serial.println(measured_altitude,2);
          }
        }
        else if(uart_class==HEARTBEAT)
        {
          heartbeat_counter = 0;
          if(USER_SERIAL) Serial.println("heartbeat");
        }
        else
        {
          if(USER_SERIAL) Serial.print("Debug: ");
          if(USER_SERIAL) Serial.println(token);
        }
      }
      else if(index==2)
      {
          degrees2 = atof(token);
          if(uart_class==TARGET_UPDATE) 
          {
            set_target_azimuth = (degrees2);
            if(USER_SERIAL) Serial.print("setting target azimuth: ");
            target_azimuth = set_target_azimuth;
            if(USER_SERIAL) Serial.println(target_azimuth, 2);
          }
        
      }
      else if(USER_SERIAL) Serial.println("comms error - ard parsing");
      token = strtok(NULL, ",");
      index++;
    }
  }
}

void menu_fx(void)
{ 
  switch(menu_state)
  {
    case main_menu:
      if(menu_first_time)
      {
        menu_first_time = 0;
        if(USER_SERIAL) Serial.println("main menu");
        Serial2.println("mm");
        tracking_program_flag = 0;
        stow_program_flag = 0;
        zero_program_flag = 0;
        motor_test_flag = 0;
        wake_test_flag = 0;
      }
      break;
    case tracking_program:
      if(menu_first_time)
      {
        menu_first_time = 0;
        if(USER_SERIAL) Serial.println("starting tracking");
        Serial2.println("st t");
        tracking_program_flag = 1;
        execute_track_program(1);//init
        stow_program_flag = 0;
        zero_program_flag = 0;
        motor_test_flag = 0;
        wake_test_flag = 0;
      }
    break;
    case store_program:
      if(menu_first_time)
      {
        menu_first_time = 0;
        if(USER_SERIAL) Serial.println("starting store program");
        Serial2.println("st s p");
        stow_program_flag = 1;
        tracking_program_flag = 0;
        zero_program_flag = 0;
        motor_test_flag = 0;
        wake_test_flag = 0;
      }
      if(stow_program_flag==0)
      {
        menu_state = main_menu;
        menu_first_time = 1;
      }
    break;
    case wake_program:
      if(menu_first_time)
      {
        menu_first_time = 0;
        if(USER_SERIAL) Serial.println("starting waking program");
        Serial2.println("st w p");
        zero_program_flag = 0;
        tracking_program_flag = 0;
        stow_program_flag = 0;
        motor_test_flag = 0;
        wake_test_flag = 1;
      }
      if(wake_test_flag==0)
      {
        menu_state = main_menu;
        menu_first_time = 1;
      }
    case motor_test_program:
    if(menu_first_time)
    {
      if(USER_SERIAL) Serial.println("motor test");
      Serial2.println("HB_f");
      menu_first_time = 0;
      tracking_program_flag = 0;
      stow_program_flag = 0;
      zero_program_flag = 0;
      motor_test_flag = 1;
      wake_test_flag = 0;
    }
    break;
    default:
    break;
  }
}
void send_position_serial(float pitch, float roll, float yaw, float az, float ze)
{
  //make string
  String publish_data = "gyro: " + String(pitch) + "," + String(roll) + "," + String(yaw) + "," + String(ze) + "," + String(az); 
  if(USER_SERIAL) Serial.println(publish_data);
  Serial2.println(publish_data);
}

void MCD_setup(void)
{
  analogWrite(MOTOR_AZ_DRIVE, 0);
  analogWrite(MOTOR_ZE_DRIVE, 0);
  pinMode(MOTOR_AZ_DIR, OUTPUT);
  digitalWrite(MOTOR_AZ_DIR, LOW);
  pinMode(MOTOR_ZE_DIR, OUTPUT);
  digitalWrite(MOTOR_ZE_DIR, LOW);
  HE_counter_AZ = 0;
  HE_counter_ZE = 0;
}

void mcd_drive(uint8_t motor, uint8_t direction, uint8_t drive)
{
  if(motor==MOTOR_AZ_DRIVE)
  {
    attachInterrupt(digitalPinToInterrupt(HE_1_AZ),he_1_change_AZ,LOW);
    attachInterrupt(digitalPinToInterrupt(HE_2_AZ),he_2_change_AZ,LOW);
    digitalWrite(MOTOR_AZ_DIR, direction);
    analogWrite(MOTOR_AZ_DRIVE, drive);
    roll_direction = direction;
  }
  else 
  {
    attachInterrupt(digitalPinToInterrupt(HE_1_ZE),he_1_change_ZE,LOW);
    attachInterrupt(digitalPinToInterrupt(HE_2_ZE),he_2_change_ZE,LOW);
    //enable_ze_HE_monitor();    
    digitalWrite(MOTOR_ZE_DIR, direction);
    analogWrite(MOTOR_ZE_DRIVE, drive);
    pitch_direction = direction;
  }
}

void mcd_stop(void)
{
  analogWrite(MOTOR_AZ_DRIVE, 0);
  analogWrite(MOTOR_ZE_DRIVE, 0);
  detachInterrupt(digitalPinToInterrupt(HE_1_AZ));
  detachInterrupt(digitalPinToInterrupt(HE_2_AZ));
  detachInterrupt(digitalPinToInterrupt(HE_1_ZE));
  detachInterrupt(digitalPinToInterrupt(HE_2_ZE));
  //disable_ze_HE_monitor();
}

void setup() {
  MCD_setup();

  // Set the Timer that controls the System Ticker
  Timer1.initialize(SYSTEM_TICK); // microseconds
  Timer1.attachInterrupt(isr, SYSTEM_TICK);

  //if(USER_SERIAL) 
  Serial.setTimeout(1000);
  Serial.begin(115200);
  if(USER_SERIAL) while(!Serial) delay(10);

  Serial2.setTimeout(1000);
  Serial2.begin(115200);
  delay(200);
  Serial2.flush();

  configure_wifi_credentials();

  wdt_enable(WDTO_4S); //Enable WDT with a timeout of 8 seconds

}

void execute_track_program(char init)
{
  static char track_state = 0;
  static float error;
  static int timeout_counter = 0;

  if(init==1) {
    track_state = 0;
    timeout_counter = 0;
  }
  else {
    switch(track_state)
    {
      case 0: //check azimuth error
        if(!(target_azimuth==-999))
        {
          error = target_azimuth - measured_azimuth;
          if(USER_SERIAL) Serial.println(error);
          if(error>ALLOWABLE_ERROR_HE) 
          {
            if(USER_SERIAL) Serial.println("AZ +");
            mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
            track_state++;
          }
          else if(error<(-1*ALLOWABLE_ERROR_HE)) 
          {
            if(USER_SERIAL) Serial.println("AZ -");
            mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
            track_state++;
          }
          else track_state = track_state + 2;
          timeout_counter = 0;
        }
        if(timeout_counter>=MOTOR_TIMEOUT)
        {
          mcd_stop();
          //FLAG ERROR!
          if(USER_SERIAL) Serial.println("track timeout");
          Serial2.println("track timeout");
          tracking_program_flag = 0;
          menu_state = main_menu;
          menu_first_time = 1;
        }
        else timeout_counter++;
        break;
      case 1:
        error = target_azimuth - measured_azimuth;
        if(USER_SERIAL) Serial.println(error);
        if(error>ALLOWABLE_ERROR_HE) mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
        else if(error<(-1*ALLOWABLE_ERROR_HE)) mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
        else
        {
          mcd_stop();        
          track_state++;
          timeout_counter = 0;
        }
        if(timeout_counter>=MOTOR_TIMEOUT)
        {
          mcd_stop();
          //FLAG ERROR!
          if(USER_SERIAL) Serial.println("track timeout");
          Serial2.println("track timeout");
          tracking_program_flag = 0;
          menu_state = main_menu;
          menu_first_time = 1;
        }
        else timeout_counter++;
        break;
      case 2: //check zenith error
        if(!(target_altitude == -999))
        {
          error = target_altitude - (measured_altitude);
          if(USER_SERIAL) Serial.println(error);
          if(error>ALLOWABLE_ERROR) 
          {
            if(PITCH_POLARITY_1) 
            {
              if(USER_SERIAL) Serial.println("Motor driving");
              mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
            }
            else 
            {
              if(USER_SERIAL) Serial.println("Motor driving");
              mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
            }
            track_state++;
          }
          else if(error<(-1*ALLOWABLE_ERROR)) 
          {
            if(PITCH_POLARITY_1) 
            {
              if(USER_SERIAL) Serial.println("Motor driving");
              mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
            }
            else 
            {
              if(USER_SERIAL) Serial.println("Motor driving");
              mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
            }
            track_state++;
          }
          else track_state = 0;
          timeout_counter = 0;
        }
        else
        {
          if(USER_SERIAL) Serial.println("Zero gyroscope before running program.");
          mcd_stop();        
          tracking_program_flag=0;
          timeout_counter = 0;
        }
        break;
      case 3:
        error = target_altitude - (measured_altitude);
        if(USER_SERIAL) Serial.println(error);
        if(error>ALLOWABLE_ERROR) 
        {
          if(PITCH_POLARITY_1) mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
          else mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
        }
        else if(error<(-1*ALLOWABLE_ERROR)) 
        {
          if(PITCH_POLARITY_1) mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
          else mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
        }
        else
        {
          mcd_stop();        
          track_state=0;
          timeout_counter = 0;
        }
        if(timeout_counter>=MOTOR_TIMEOUT)
        {
          mcd_stop();
          //FLAG ERROR!
          if(USER_SERIAL) Serial.println("motor timeout");
          Serial2.println("motor timeout");
          tracking_program_flag = 0;
          menu_state = main_menu;
          menu_first_time = 1;
        }
        else timeout_counter++;
    }
  }
}

void execute_wake_program(void)
{
  // move to 180, 0.
  static char wake_state = 0;
  static char wake_first_time = 1;
  static float error;

  switch(wake_state)
  {
    case 0: //check zenith error
      error = TARGET_WAKE_ZENITH - (measured_altitude);
      if(USER_SERIAL) Serial.println(error);
      if(error>ALLOWABLE_ERROR) 
      {
        if(PITCH_POLARITY_1) mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
        else mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
        wake_state++;
      }
      else if(error<(-1*ALLOWABLE_ERROR)) 
      {
        if(PITCH_POLARITY_1) mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
        else mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
        wake_state++;
      }
      else 
      {
        wake_state = wake_state + 2;
      }
      break;
    case 1:
      error = TARGET_WAKE_ZENITH - (measured_altitude);
      if(USER_SERIAL) Serial.println(error);
      if(error>ALLOWABLE_ERROR) 
      {
        if(PITCH_POLARITY_1) mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
        else mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
      }
      else if(error<(-1*ALLOWABLE_ERROR)) 
      {
        if(PITCH_POLARITY_1) mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
        else mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
      }
      else 
      {
        mcd_stop();        
        wake_state++;
      }
      break;
    case 2: //check azimuth error
      error = TARGET_WAKE_AZIMUTH - measured_azimuth;
      if(USER_SERIAL) Serial.println(error);
      if(error>ALLOWABLE_ERROR_HE) 
      {
        if(USER_SERIAL) Serial.println('1');
        mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
        wake_state++;
      }
      else if(error<(-1*ALLOWABLE_ERROR_HE)) 
      {
        if(USER_SERIAL) Serial.println('2');
        mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
        wake_state++;
      }
      else 
      {
        mcd_stop();
        wake_test_flag = 0;
        wake_state = 0;
      }
      break;
    case 3:
      error = TARGET_WAKE_AZIMUTH - measured_azimuth;
      if(USER_SERIAL) Serial.println(error);
      if(error>ALLOWABLE_ERROR_HE) mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
      else if(error<(-1*ALLOWABLE_ERROR_HE)) mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
      else
      {
        mcd_stop();        
        wake_state=0;
        wake_test_flag=0;
      }
      break;
  }
}

void execute_motor_testing(void)
{
  static long pulse_count_local;
  long temp_pulse_delta;
  static int print_timer = 0;
  switch(motor_state)
  {
    case 0:
    if(motor_state_first_time)
    {
      if(USER_SERIAL) Serial.println("stop motor");
      motor_state_first_time = 0;
      mcd_stop();  //stop motors
    }
    break;
    case 1:
    if(motor_state_first_time)
    {
      if(USER_SERIAL) Serial.println("az pos");
      motor_state_first_time = 0;
      pulse_count_local = HE_counter_AZ;
      mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
      print_timer = 0;
    }
    if(print_timer>=PRINT_TIME_COUNTS_100MS) //100ms increments
    {
      print_timer = 0;
      temp_pulse_delta = HE_counter_AZ-pulse_count_local;
      String publish_string = "pulses: " + String(temp_pulse_delta) + ", output degrees: " + String(measured_azimuth);
      if(USER_SERIAL) Serial.println(publish_string);
      Serial2.println(publish_string);
    }
    else print_timer++;
    break;
    case 2:
    if(motor_state_first_time)
    {
      if(USER_SERIAL) Serial.println("az neg");
      motor_state_first_time = 0;
      pulse_count_local = HE_counter_AZ;
      mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
      print_timer = 0;
    }
    if(print_timer>=PRINT_TIME_COUNTS_100MS)
    {
      print_timer = 0;
      temp_pulse_delta = HE_counter_AZ-pulse_count_local;
      String publish_string = "pulses: " + String(temp_pulse_delta) + ", output degrees: " + String(measured_azimuth);
      if(USER_SERIAL) Serial.println(publish_string);
      Serial2.println(publish_string);
    }
    else print_timer++;
    break;
    case 3:
    if(motor_state_first_time)
    {
      if(USER_SERIAL) Serial.println("ze pos");
      motor_state_first_time = 0;
      pulse_count_local = HE_counter_ZE;
      mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
      print_timer = 0;
    }
    if(print_timer>=PRINT_TIME_COUNTS_100MS)
    {
      print_timer = 0;
      temp_pulse_delta = HE_counter_ZE-pulse_count_local;
      String publish_string = "pulses: " + String(temp_pulse_delta) + ", output degrees: " + String(measured_altitude);
      if(USER_SERIAL) Serial.println(publish_string);
      Serial2.println(publish_string);
    }
    else print_timer++;
    break;
    case 4:
    if(motor_state_first_time)
    {
      if(USER_SERIAL) Serial.println("ze neg");
      motor_state_first_time = 0;
      pulse_count_local = HE_counter_ZE;
      mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
      print_timer = 0;
    }
    if(print_timer>=PRINT_TIME_COUNTS_100MS)
    {
      print_timer = 0;
      temp_pulse_delta = HE_counter_ZE-pulse_count_local;
      String publish_string = "pulses: " + String(temp_pulse_delta) + ", output degrees: " + String(measured_altitude);
      if(USER_SERIAL) Serial.println(publish_string);
      Serial2.println(publish_string);
    }
    else print_timer++;
    break;
    default:
      mcd_stop();
    break;
  }  
}

void execute_stow_program(void)
{
  // move to 180, 0.
  static char stow_state = 0;
  static float error;

  switch(stow_state)
  {
    case 0: //check azimuth error
      error = TARGET_STOW_AZIMUTH - measured_azimuth;
      if(USER_SERIAL) Serial.println(error);
      if(error>ALLOWABLE_ERROR_HE) 
      {
        if(USER_SERIAL) Serial.println('1');
        mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
        stow_state++;
      }
      else if(error<(-1*ALLOWABLE_ERROR_HE)) 
      {
        if(USER_SERIAL) Serial.println('2');
        mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
        stow_state++;
      }
      else stow_state = stow_state + 2;
      break;
    case 1:
      error = TARGET_STOW_AZIMUTH - measured_azimuth;
      if(USER_SERIAL) Serial.println(error);
      if(error>ALLOWABLE_ERROR_HE) mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
      else if(error<(-1*ALLOWABLE_ERROR_HE)) mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
      else
      {
        mcd_stop();        
        stow_state++;
      }
      break;
    case 2: //check zenith error
      error = TARGET_STOW_ZENITH - (measured_altitude);
      if(USER_SERIAL) Serial.println(error);
      if(error>ALLOWABLE_ERROR) 
      {
        if(PITCH_POLARITY_1) mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
        else mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
        stow_state++;
      }
      else if(error<(-1*ALLOWABLE_ERROR)) 
      {
        if(PITCH_POLARITY_1) mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
        else mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
        stow_state++;
      }
      else 
      {
        stow_program_flag = 0;
        stow_state = 0;
      }
      break;
    case 3:
      error = TARGET_STOW_ZENITH - (measured_altitude);
      if(USER_SERIAL) Serial.println(error);
      if(error>ALLOWABLE_ERROR) 
      {
        if(PITCH_POLARITY_1) mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
        else mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
      }
      else if(error<(-1*ALLOWABLE_ERROR)) 
      {
        if(PITCH_POLARITY_1) mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
        else mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
      }
      else
      {
        mcd_stop();        
        stow_program_flag=0;
        stow_state =0;
      }
  }
}

void update_absolute_measured_azimuth(double val)
{
  measured_azimuth = val;
  local_temp_pulse = HE_counter_AZ;
}

void update_local_measured_azimuth(void)
{
  double delta_pulse; 
  long delta = HE_counter_AZ-local_temp_pulse;
  delta_pulse = delta/792.22; // gear ratio is 575:1, then 62:1
  if(roll_direction==AZIMUTH_DIRECTION_POSITIVE) measured_azimuth+=delta_pulse;
  else measured_azimuth-=delta_pulse;
  //handle rollover
  if(measured_azimuth<0) measured_azimuth = 360+measured_azimuth;
  if(measured_azimuth>360) measured_azimuth = measured_azimuth-360;
  local_temp_pulse = HE_counter_AZ;
}

void update_absolute_measured_altitude(double val)
{
  measured_altitude = val;
  local_temp_pulse_ZE = HE_counter_ZE;
}

void update_local_measured_altitude(void)
{
  double delta_pulse; 
  long delta = HE_counter_ZE-local_temp_pulse_ZE;
  delta_pulse = delta/792.22; // gear ratio is 575:1, then 62:1
  if(pitch_direction==ZENITH_DIRECTION_POSITIVE) measured_altitude+=delta_pulse;
  else measured_altitude-=delta_pulse;
  //handle rollover
  if(measured_altitude<0) measured_altitude = 360+measured_altitude;
  if(measured_altitude>360) measured_altitude = measured_altitude-360;
  local_temp_pulse_ZE = HE_counter_ZE;
}


void loop() {

  // Synchronized activities at different time intervals, every 1ms
  if(b1MSCounter >= 1){
    b1MSCounter = 0; 
    b10MSCounter++; 
  
  }
  // Every 10ms
  if(b10MSCounter >= 10){
    b10MSCounter=0; 
    b100MSCounter++;

  }

  // Every 100ms
  if(b100MSCounter >= 10){
    b100MSCounter = 0; 
    b1SCounter++;     
    
    
    serial_rx();
    menu_fx();

    update_local_measured_azimuth();
    update_local_measured_altitude();
    if(tracking_program_flag) execute_track_program(0);
    if(stow_program_flag) execute_stow_program();
    if(wake_test_flag) execute_wake_program();
    //if(!zero_program_flag) lcd_display(measured_altitude, measured_azimuth, yaw_global);
    if(motor_test_flag) execute_motor_testing();

    wdt_reset(); //Reset the watchdog
  }

  if(b1SCounter >= 10) {
    b1SCounter=0;
    b5SCounter++;

    if(heartbeat_counter>=HEARTBEAT_TIMEOUT_SECONDS)
    {
      if(heartbeat_counter==HEARTBEAT_TIMEOUT_SECONDS)
      {
          mcd_stop();
          init_menu();
          if(USER_SERIAL) Serial.println("HB failure");
          Serial2.println("HB failure");
          tracking_program_flag = 0;
          stow_program_flag = 0;
          zero_program_flag = 0;
          motor_test_flag = 0;
          heartbeat_counter++;
      }
    }
    else heartbeat_counter++;
  }
  if(b5SCounter >= 2)
  {
    b5SCounter = 0;
    
    if(tracking_program_flag) send_position_serial(measured_altitude, measured_azimuth, yaw_global, target_azimuth, target_altitude);
    Serial.println(".");
  }

    
}


// This is the system clock
void isr() {

  Timer1.detachInterrupt();

  systemClk++;

  if (systemClk >= (NUMTICKS_1MS)) {
    b1MSCounter++;
    systemClk = 0; 
  }
    
  Timer1.attachInterrupt(isr,SYSTEM_TICK);     
}

void he_1_change_AZ(void)
{
  detachInterrupt(digitalPinToInterrupt(HE_1_AZ));
  HE_counter_AZ++;
  if(HE_counter_AZ>=target_pulse_count_AZ)
  {
    target_pulse_reached_AZ = 1;
  }
  attachInterrupt(digitalPinToInterrupt(HE_1_AZ),he_1_change_AZ,CHANGE);
}

void he_2_change_AZ(void)
{
  detachInterrupt(digitalPinToInterrupt(HE_2_AZ));
  HE_counter_AZ++;
  if(HE_counter_AZ>=target_pulse_count_AZ)
  {
    target_pulse_reached_AZ = 1;
  }
  attachInterrupt(digitalPinToInterrupt(HE_2_AZ),he_2_change_AZ,CHANGE);
}

void he_1_change_ZE(void)
{
  detachInterrupt(digitalPinToInterrupt(HE_1_ZE));
  HE_counter_ZE++;
  if(HE_counter_ZE>=target_pulse_count_ZE)
  {
    target_pulse_reached_ZE = 1;
  }
  attachInterrupt(digitalPinToInterrupt(HE_1_ZE),he_1_change_ZE,CHANGE);
}

void he_2_change_ZE(void)
{
  detachInterrupt(digitalPinToInterrupt(HE_2_ZE));
  HE_counter_ZE++;
  if(HE_counter_ZE>=target_pulse_count_ZE)
  {
    target_pulse_reached_ZE = 1;
  }
  attachInterrupt(digitalPinToInterrupt(HE_2_ZE),he_2_change_ZE,CHANGE);
}

void enable_ze_HE_monitor(void)
{
  ze_monitor = 1;  
}
void disable_ze_HE_monitor(void)
{
  ze_monitor = 0;  
}

void ZE_HE_monitor(void)
{
  static char old_val_1 = 0;
  static int change_counter_1 = 0;
  static char old_val_2 = 0;
  static int change_counter_2 = 0;

  if(ze_monitor)
  {
    char val1 = digitalRead(HE_1_ZE);
    if(val1==old_val_1)
    {
      if(change_counter_1==2)
      {
        
          HE_counter_ZE++;
          if(HE_counter_ZE>=target_pulse_count_ZE)
          {
            target_pulse_reached_ZE = 1;
          }
          change_counter_1++;
      }
      else if(change_counter_1<2) change_counter_1++;
    }
    else
    {
      change_counter_1 = 0;
    }
    old_val_1 = val1;
    
    char val2 = digitalRead(HE_2_ZE);
    if(val2==old_val_2)
    {
      if(change_counter_2==2)
      {
        
          HE_counter_ZE++;
          if(HE_counter_ZE>=target_pulse_count_ZE)
          {
            target_pulse_reached_ZE = 1;
          }
          change_counter_2++;
      }
      else if(change_counter_2<2) change_counter_2++;
    }
    else
    {
      change_counter_2 = 0;
    }
    old_val_2 = val2;
  }
}