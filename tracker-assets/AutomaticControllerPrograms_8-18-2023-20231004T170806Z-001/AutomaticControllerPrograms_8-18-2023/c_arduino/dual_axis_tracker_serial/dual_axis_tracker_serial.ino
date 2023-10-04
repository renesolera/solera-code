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
 

***********************/

#include "TimerOne.h"       // Avaiable from http://www.arduino.cc/playground/Code/Timer1
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

LiquidCrystal_I2C lcd(0x27,16,2); // set the LCD address to 0x3F for a 16 chars and 2 line display
//LiquidCrystal_I2C lcd(0x3F,16,2); // set the LCD address to 0x3F for a 16 chars and 2 line display

#define SYSTEM_TICK 100
#define NUMTICKS_1MS  10
//timing variables
volatile uint32_t systemClk = 0;
volatile uint8_t b1MSCounter = 0;
uint8_t b10MSCounter = 0;
uint8_t b100MSCounter = 0;
uint8_t b1SCounter = 0;

uint8_t debug_LED = 1;

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

const int MPU = 0x68; // MPU6050 I2C address
float AccX, AccY, AccZ;
float GyroX, GyroY, GyroZ;
float accAngleX = 0;
float accAngleY = 0;
float gyroAngleX = 0;
float gyroAngleY = 0;
float gyroAngleZ = 0;
float AccErrorX = 0;
float AccErrorY = 0;
float GyroErrorX = 0;
float GyroErrorY = 0;
float GyroErrorZ = 0;
float elapsedTime, currentTime, previousTime;
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
#define MOTOR_AZ_DIR (8)
#define MOTOR_ZE_DIR (13)
#define HE_1_AZ  (2)
#define HE_2_AZ  (3)
#define HE_1_ZE  (18)
#define HE_2_ZE  (19)
#define MAX_ALTITUDE_ALLOWABLE  (86.5)
#define PITCH_POLARITY_1  (0)

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

#define HEARTBEAT_TIMEOUT_SECONDS (45)

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
  while (Serial.available()>0)
  {
    bytes_read = Serial.readBytesUntil('\n', ser_vals, sizeof(ser_vals)-1);
    ser_vals[bytes_read] = '\0';
  }
  if(bytes_read>0) 
  {
    uint32_t * header;
    i=0;
    while(i<bytes_read)
    {
      //scan for header
      header = (uint32_t*) &ser_vals[i];
      uint32_t swapped = ((*header>>24)&0xff) | // move byte 3 to byte 0
                    ((*header<<8)&0xff0000) | // move byte 1 to byte 2
                    ((*header>>8)&0xff00) | // move byte 2 to byte 1
                    ((*header<<24)&0xff000000); // byte 0 to byte 3
      if(swapped==uart_header) break;
      i++;
    }
    if(i==bytes_read) return 1; //no header found
    i=i+4; //length of header
    uint8_t uart_class = (uint8_t) (ser_vals[i]); //convert to int
    i++;
    uint8_t uart_payload_len = (uint8_t) (ser_vals[i]); //convert to int 
    i++;
    char payload[25];
    memcpy(payload, &ser_vals[i], uart_payload_len);
    payload[uart_payload_len] = '\0';

    Serial.print("class: ");
    Serial.print(uart_class);
    Serial.print(", payload len: ");
    Serial.print(uart_payload_len);
    Serial.print(", payload: ");
    Serial.println(payload);

    if(uart_class==TARGET_UPDATE) 
    {
      float set_target_altitude, set_target_azimuth;
      Serial.println(payload);
      for(x=0;x<uart_payload_len;x++) if(payload[x]==44) break;
      memcpy(substr, &payload[0], x);
      substr[x] = '\0';
      set_target_altitude = atof(substr);
      if(set_target_altitude>MAX_ALTITUDE_ALLOWABLE)
      {
        Serial.print("altitude target too high, setting to max: ");
        set_target_altitude = MAX_ALTITUDE_ALLOWABLE;
      }
      else Serial.print("setting target altitude: ");
      target_altitude = set_target_altitude;
      Serial.println(target_altitude, 3);
      for(int j=0;j<8;j++) substr[j] = 0x00;

      memcpy(substr, &payload[x+1], (uart_payload_len-x-1));
      substr[uart_payload_len-x-1] = '\0';
      set_target_azimuth = atof(substr);
      Serial.print("setting target azimuth: ");
      target_azimuth = set_target_azimuth;
      Serial.println(target_azimuth, 3);
      for(int j=0;j<8;j++) substr[j] = 0x00;
    }
    else if(uart_class==MENU_INPUT) 
    {
      uint8_t received_char = (payload[0]);
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
    else if(uart_class==AZ_UPDATE) 
    {
      float set_current_azimuth;
      Serial.println(payload);
      memcpy(substr, &payload[0], uart_payload_len);
      substr[uart_payload_len] = '\0';
      set_current_azimuth = atof(substr);
      measured_azimuth = set_current_azimuth;
      Serial.print("setting current azimuth: ");
      Serial.println(measured_azimuth, 3);
      for(int j=0;j<8;j++) substr[j] = 0x00;
    }
    else if(uart_class==ALT_UPDATE) 
    {
      float set_current_altitude;
      Serial.println(payload);
      memcpy(substr, &payload[0], uart_payload_len);
      substr[uart_payload_len] = '\0';
      set_current_altitude = atof(substr);
      measured_altitude = set_current_altitude;
      Serial.print("setting current altitude: ");
      Serial.println(measured_altitude, 3);
      for(int j=0;j<8;j++) substr[j] = 0x00;
    }
    else if(uart_class==HEARTBEAT) 
    {
      heartbeat_counter = 0;
    }
    else if(uart_class==DEBUG) 
    {
      Serial.println("debug message...");
    }
    else Serial.println("comms error - ard parsing");
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
        Serial.println("main menu");
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
        Serial.println("starting tracking");
        tracking_program_flag = 1;
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
        Serial.println("starting store program");
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
        Serial.println("starting waking program");
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
      Serial.println("motor test");
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

void init_LCD(void)
{
  lcd.init(); //init lcd
  lcd.backlight(); //turn on backlight
  lcd.setCursor(0,0); // set the cursor to column 1, line 0
  lcd.print("P: ");
}

void lcd_display(float pitch, float roll, float yaw)
{
  lcd.setCursor(0,0); // set the cursor to column 1, line 0
  lcd.print("P: ");
  lcd.print(pitch);
  lcd.setCursor(0,1);
  lcd.print("R: ");
  lcd.print(roll);
  lcd.setCursor(8,1);
  lcd.print("Y:");
  lcd.print(yaw);
}

void send_position_serial(float pitch, float roll, float yaw, float az, float ze)
{
  Serial.print("gyro:");
  Serial.print(pitch, 3);
  Serial.print(", ");
  Serial.print(roll, 3);
  Serial.print(", ");
  Serial.print(yaw, 3);
  Serial.print(", ");
  Serial.print(ze, 3);
  Serial.print(", ");
  Serial.print(az, 3);
  Serial.println();
}

void init_MPU6050(void)
{
  Wire.begin();                      // Initialize comunication
  Wire.beginTransmission(MPU);       // Start communication with MPU6050 // MPU=0x68
  Wire.write(0x6B);                  // Talk to the register 6B
  Wire.write(0x00);                  // Make reset - place a 0 into the 6B register
  Wire.endTransmission(true);        //end the transmission
  
  // Configure Accelerometer Sensitivity - Full Scale Range (default +/- 2g)
  Wire.beginTransmission(MPU);
  Wire.write(0x1C);                  //Talk to the ACCEL_CONFIG register (1C hex)
  Wire.write(0x10);                  //Set the register bits as 00010000 (+/- 8g full scale range)
  Wire.endTransmission(true);
  // Configure Gyro Sensitivity - Full Scale Range (default +/- 250deg/s)
  Wire.beginTransmission(MPU);
  Wire.write(0x1B);                   // Talk to the GYRO_CONFIG register (1B hex)
  Wire.write(0x10);                   // Set the register bits as 00010000 (1000deg/s full scale)
  Wire.endTransmission(true);
  delay(20);
  
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
    attachInterrupt(digitalPinToInterrupt(HE_1_AZ),he_1_change_AZ,CHANGE);
    attachInterrupt(digitalPinToInterrupt(HE_2_AZ),he_2_change_AZ,CHANGE);
    digitalWrite(MOTOR_AZ_DIR, direction);
    analogWrite(MOTOR_AZ_DRIVE, drive);
    roll_direction = direction;
  }
  else 
  {
    attachInterrupt(digitalPinToInterrupt(HE_1_ZE),he_1_change_ZE,CHANGE);
    attachInterrupt(digitalPinToInterrupt(HE_2_ZE),he_2_change_ZE,CHANGE);
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
}

void setup() {
  MCD_setup();

  // Set the Timer that controls the System Ticker
  Timer1.initialize(SYSTEM_TICK); // microseconds
  Timer1.attachInterrupt(isr, SYSTEM_TICK);

  Serial.begin(9600);
  while(!Serial) delay(10);
  init_LCD();
}

void execute_track_program(void)
{
  static char track_state = 0;
  static float error;
  static int timeout_counter = 0;

  static char old_state = 10;

  if(old_state!=track_state)
  {
    Serial.print("ts: ");
    Serial.println(track_state);
    old_state = track_state;
  }

  switch(track_state)
  {
    case 0: //check azimuth error
      if(!(target_azimuth==-999))
      {
        error = target_azimuth - measured_azimuth;
        Serial.println(error);
        if(error>ALLOWABLE_ERROR_HE) 
        {
          Serial.println("AZ +");
          mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
          track_state++;
        }
        else if(error<(-1*ALLOWABLE_ERROR_HE)) 
        {
          Serial.println("AZ -");
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
        Serial.println("track timeout");
        tracking_program_flag = 0;
        menu_state = main_menu;
        menu_first_time = 1;
      }
      else timeout_counter++;
      break;
    case 1:
      error = target_azimuth - measured_azimuth;
      Serial.println(error);
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
        Serial.println("track timeout");
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
        Serial.println(error);
        if(error>ALLOWABLE_ERROR) 
        {
          if(PITCH_POLARITY_1) 
          {
            Serial.println("Motor driving");
            mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
          }
          else 
          {
            Serial.println("Motor driving");
            mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
          }
          track_state++;
        }
        else if(error<(-1*ALLOWABLE_ERROR)) 
        {
          if(PITCH_POLARITY_1) 
          {
            Serial.println("Motor driving");
            mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
          }
          else 
          {
            Serial.println("Motor driving");
            mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
          }
          track_state++;
        }
        else track_state = 0;
        timeout_counter = 0;
      }
      else
      {
        Serial.println("Zero gyroscope before running program.");
        mcd_stop();        
        tracking_program_flag=0;
        timeout_counter = 0;
      }
      break;
    case 3:
      error = target_altitude - (measured_altitude);
      Serial.println(error);
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
        Serial.println("motor timeout");
        tracking_program_flag = 0;
        menu_state = main_menu;
        menu_first_time = 1;
      }
      else timeout_counter++;
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
      Serial.println(error);
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
      Serial.println(error);
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
      Serial.println(error);
      if(error>ALLOWABLE_ERROR_HE) 
      {
        Serial.println('1');
        mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
        wake_state++;
      }
      else if(error<(-1*ALLOWABLE_ERROR_HE)) 
      {
        Serial.println('2');
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
      Serial.println(error);
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
      Serial.println("stop motor");
      motor_state_first_time = 0;
      mcd_stop();  //stop motors
    }
    break;
    case 1:
    if(motor_state_first_time)
    {
      Serial.println("az pos");
      motor_state_first_time = 0;
      pulse_count_local = HE_counter_AZ;
      mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
      print_timer = 0;
    }
    if(print_timer>=5)
    {
      print_timer = 0;
      Serial.print("pulses: ");
      temp_pulse_delta = HE_counter_AZ-pulse_count_local;
      Serial.print(temp_pulse_delta);
      Serial.print(", \t ");
      Serial.print("output degrees: ");
      Serial.println(measured_azimuth);
    }
    else print_timer++;
    break;
    case 2:
    if(motor_state_first_time)
    {
      Serial.println("az neg");
      motor_state_first_time = 0;
      pulse_count_local = HE_counter_AZ;
      mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
      print_timer = 0;
    }
    if(print_timer>=5)
    {
      print_timer = 0;
      Serial.print("pulses: ");
      temp_pulse_delta = HE_counter_AZ-pulse_count_local;
      Serial.print(temp_pulse_delta);
      Serial.print(", \t ");
      Serial.print("output degrees: ");
      Serial.println(measured_azimuth);
    }
    else print_timer++;
    break;
    case 3:
    if(motor_state_first_time)
    {
      Serial.println("ze pos");
      motor_state_first_time = 0;
      pulse_count_local = HE_counter_ZE;
      mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
      print_timer = 0;
    }
    if(print_timer>=5)
    {
      print_timer = 0;
      Serial.print("pulses: ");
      temp_pulse_delta = HE_counter_ZE-pulse_count_local;
      Serial.print(temp_pulse_delta);
      Serial.print(", \t ");
      Serial.print("output degrees: ");
      Serial.println(measured_altitude);
    }
    else print_timer++;
    break;
    case 4:
    if(motor_state_first_time)
    {
      Serial.println("ze neg");
      motor_state_first_time = 0;
      pulse_count_local = HE_counter_ZE;
      mcd_drive(MOTOR_ZE_DRIVE, ZENITH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
      print_timer = 0;
    }
    if(print_timer>=5)
    {
      print_timer = 0;
      Serial.print("pulses: ");
      temp_pulse_delta = HE_counter_ZE-pulse_count_local;
      Serial.print(temp_pulse_delta);
      Serial.print(", \t ");
      Serial.print("output degrees: ");
      Serial.println(measured_altitude);
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
      Serial.println(error);
      if(error>ALLOWABLE_ERROR_HE) 
      {
        Serial.println('1');
        mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_POSITIVE, MOTOR_DRIVE_STRENGTH);
        stow_state++;
      }
      else if(error<(-1*ALLOWABLE_ERROR_HE)) 
      {
        Serial.println('2');
        mcd_drive(MOTOR_AZ_DRIVE, AZIMUTH_DIRECTION_NEGATIVE, MOTOR_DRIVE_STRENGTH);
        stow_state++;
      }
      else stow_state = stow_state + 2;
      break;
    case 1:
      error = TARGET_STOW_AZIMUTH - measured_azimuth;
      Serial.println(error);
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
      Serial.println(error);
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
      Serial.println(error);
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


    //using HE sensors// if(!zero_program_flag) accel_readings();
  }

  // Every 100ms
  if(b100MSCounter >= 10){
    b100MSCounter = 0; 
    b1SCounter++;     
    
    serial_rx();
    menu_fx();

    update_local_measured_azimuth();
    update_local_measured_altitude();
    if(tracking_program_flag) execute_track_program();
    if(stow_program_flag) execute_stow_program();
    if(wake_test_flag) execute_wake_program();
    if(!zero_program_flag) lcd_display(measured_altitude, measured_azimuth, yaw_global);
    if(motor_test_flag) execute_motor_testing();
  }

  if(b1SCounter >= 10) {
    b1SCounter=0;

    if(tracking_program_flag) send_position_serial(measured_altitude, measured_azimuth, yaw_global, target_azimuth, target_altitude);
    
    if(heartbeat_counter>=HEARTBEAT_TIMEOUT_SECONDS)
    {
      if(heartbeat_counter==HEARTBEAT_TIMEOUT_SECONDS)
      {
          mcd_stop();
          init_menu();
          Serial.println("HB failure");
          tracking_program_flag = 0;
          stow_program_flag = 0;
          zero_program_flag = 0;
          motor_test_flag = 0;
          heartbeat_counter++;
      }
    }
    else heartbeat_counter++;
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