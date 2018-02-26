/**
 * This program logs data to a binary file.  
 */
#include <SPI.h>
#include <SdFat.h>
#include <FreeStack.h>
#include <Adafruit_GPS.h>
#include "UserDataType.h"  // Edit this include file to change data_t.
#include <Adafruit_MAX31855.h>

//------------------------------------------------------------------------------
// Set useSharedSpi true for use of an SPI sensor.
// May not work for some cards.
const bool useSharedSpi = false;

uint32_t timeI;
// initial reference time from GPS
uint32_t time0;
uint16_t year;
uint8_t month, day, hour, minute, second;

bool gpslog=true;
bool parset=false;
//==============================================================================
// Start of configuration constants.
//==============================================================================
//Interval between data records in microseconds.
const uint32_t LOG_INTERVAL_USEC = 500000;
//------------------------------------------------------------------------------
// Pin definitions.
//
// SD chip select pin.
#define SD_CS_PIN 4
//
// Digital pin to indicate an error, set to -1 if not used.
// The led blinks for fatal errors. The led goes on solid for SD write
// overrun errors and logging continues.
#undef ERROR_LED_PIN
const int8_t ERROR_LED_PIN = -1;
#define GPS_ENABLE 6
#define WREC 8
#define STAT 13
#define STRTB 16

//------------------------------------------------------------------------------
// File definitions.
//
// Maximum file size in blocks.
// The program creates a contiguous file with FILE_BLOCK_COUNT 512 byte blocks.
// This file is flash erased using special SD commands.  The file will be
// truncated if logging is stopped early.
// 10hr of logging at 1Hz
const uint32_t FILE_BLOCK_COUNT =  2788;

// log file base name.  Must be six characters or less.
#define FILE_BASE_NAME "FT043_"

// The logger will use SdFat's buffer 
//------------------------------------------------------------------------------

#define MAXDO   10
#define MAXCS   11
#define MAXCLK  12
Adafruit_MAX31855 thermocouple(MAXCLK, MAXCS, MAXDO);

//==============================================================================
// End of configuration constants.
//==============================================================================

//GPS config-note that anything with interrupts is ignored for now ------------
#define mySerial Serial1
Adafruit_GPS GPS(&mySerial);

// Temporary log file.  Will be deleted if a reset or power failure occurs.
#define TMP_FILE_NAME "tmp_log.bin"
// Size of file base name.  Must not be larger than six.
const uint8_t BASE_NAME_SIZE = sizeof(FILE_BASE_NAME) - 1;

SdFat sd;
SdFile binFile;
//FatFile binFile;

char binName[13] = FILE_BASE_NAME "00.bin";

// Number of data records in a block.
const uint16_t DATA_DIM = (512 - 4)/sizeof(data_t);
//Compute fill so block size is 512 bytes.  FILL_DIM may be zero.
const uint16_t FILL_DIM = 512 - 4 - DATA_DIM*sizeof(data_t);

uint8_t tbf[512];

struct block_t {
  uint16_t count;
  uint16_t pad;
  data_t data[DATA_DIM];
  uint8_t fill[FILL_DIM];
};

block_t* BUFF;


//==============================================================================
// Error messages stored in flash.
#define error(msg) errorFlash(F(msg))
//------------------------------------------------------------------------------
void errorFlash(const __FlashStringHelper* msg) {
  sd.errorPrint(msg);
  fatalBlink();
}
//------------------------------------------------------------------------------
//
void fatalBlink() {
  while (true) {
    if (ERROR_LED_PIN >= 0) {
      digitalWrite(ERROR_LED_PIN, HIGH);
      delay(200);
      digitalWrite(ERROR_LED_PIN, LOW);
      delay(200);
    }
  }
}
//------------------------------------------------------------------------------
// log data
// max number of blocks to erase per erase call
uint32_t const ERASE_SIZE = 262144L;
void logData() {
  uint32_t bgnBlock, endBlock;

  // Find unused file name.
  if (BASE_NAME_SIZE > 6) {
    error("FILE_BASE_NAME too long");
  }
  while (sd.exists(binName)) {
    if (binName[BASE_NAME_SIZE + 1] != '9') {
      binName[BASE_NAME_SIZE + 1]++;
    } else {
      binName[BASE_NAME_SIZE + 1] = '0';
      if (binName[BASE_NAME_SIZE] == '9') {
        error("Can't create file name");
      }
      binName[BASE_NAME_SIZE]++;
    }
  }
  // Delete old tmp file.
  if (sd.exists(TMP_FILE_NAME)) {
    if (!sd.remove(TMP_FILE_NAME)) {
      error("Can't remove tmp file");
    }
  }

  // Create new file.
  binFile.close();
  if (!binFile.createContiguous(sd.vwd(),
                                binName, 512 * FILE_BLOCK_COUNT)) {
    error("createContiguous failed");
  }
  upDate();
  binFile.timestamp(T_WRITE, year, month, day, hour, minute, second); 
  // Get the address of the file on the SD.
  if (!binFile.contiguousRange(&bgnBlock, &endBlock)) {
    error("contiguousRange failed");
  }
   
  // Use SdFat's internal buffer.
  uint8_t* cache = (uint8_t*)sd.vol()->cacheClear();
  if (cache == 0) {
    error("cacheClear failed");
  }

  // Flash erase all data in the file.
  uint32_t bgnErase = bgnBlock;
  uint32_t endErase;
  while (bgnErase < endBlock) {
    endErase = bgnErase + ERASE_SIZE;
    if (endErase > endBlock) {
      endErase = endBlock;
    }
    if (!sd.card()->erase(bgnErase, endErase)) {
      error("erase failed");
    }
    bgnErase = endErase + 1;
  }

  // Use SdFat buffer
  BUFF = (block_t*)cache;
  // reset count
  BUFF->count=0;

  delay(10);
  bool closeFile = false;
  uint32_t bn = 0;
  uint32_t t0 = millis();
  uint32_t t1 = t0;
  uint32_t curTime = 0;
  uint32_t count = 0;
  uint32_t ct = 0;
  uint32_t maxDelta = 0;
  uint32_t minDelta = 99999;
  uint32_t maxLatency = 0;
  uint32_t logTime = micros();

  while (1) {
    // Time for next data record.
    logTime += LOG_INTERVAL_USEC;
    
    //if process lags behind, skip a record
    if ((int32_t)(logTime - micros()) < 0) {
      continue;             
    }
    // stalls until desired logging time has been reached
    int32_t delta;
    do {
      do {
        delta = micros() - logTime;
        curTime = time0+millis()/100;
      } while (delta < 0);
    } while (curTime % 5 != 0);
    
    acquireData(&BUFF->data[BUFF->count++],curTime,ct++);

    // indicate running program
    if (digitalRead(GPS_ENABLE)==LOW && ct % 10 == 0) {
      digitalWrite(STAT,HIGH);
      delay(40);
      digitalWrite(STAT,LOW);
    }
    //write when buffer is full
   if (BUFF->count == DATA_DIM) {
      // Write block to SD.
      uint32_t usec = micros();
      if (binFile.write(BUFF,512)!=512) {
        error("write data failed");
      }
      bn++;
      if (bn % 2 == 0) binFile.sync();
       // reset count
      usec = micros() - usec;
      t1 = millis();
      if (usec > maxLatency) {
        maxLatency = usec;
      }
      BUFF->count=0;

      
      if (bn == FILE_BLOCK_COUNT) {
        // File full so stop
        break;
      }
    }
  }

  if (!binFile.close()) {
    error("file close failed");
  }

}
//------------------------------------------------------------------------------

//setup... 
void setup(void) {

  pinMode(WREC,OUTPUT);
  pinMode(STAT,OUTPUT);
  pinMode(STRTB,INPUT);
  digitalWrite(WREC,LOW);
  digitalWrite(STAT,LOW);
  
  // make sure GPS enable pin 'on' (HIGH)
  pinMode(GPS_ENABLE,OUTPUT);
  digitalWrite(GPS_ENABLE,HIGH);

  if (sizeof(block_t) != 512) {
    error("Invalid block size");
  }
  // initialize file system.
  if (!sd.begin(SD_CS_PIN, SPI_FULL_SPEED)) {
    sd.initErrorPrint();
  }

  // GPS setup -------------------------------------------------------------
  // 9600 NMEA is the default baud rate for Adafruit MTK GPS's- some use 4800
  GPS.begin(9600);
  mySerial.begin(9600);
    while (!mySerial) {
    delay(10);
  }
  // uncomment this line to turn on RMC (recommended minimum) and GGA (fix data) including altitude
  //GPS.sendCommand(PMTK_SET_NMEA_OUTPUT_RMCGGA);
  // uncomment this line to turn on only the "minimum recommended" data
  GPS.sendCommand(PMTK_SET_NMEA_OUTPUT_RMCONLY);
  
  // Set the update rate
  GPS.sendCommand(PMTK_SET_NMEA_UPDATE_5HZ);
  GPS.sendCommand(PMTK_API_SET_FIX_CTL_5HZ);
  // For the parsing code to work nicely and have time to sort thru the data, and
  // print it out we don't suggest using anything higher than 1 Hz

  // Request updates on antenna status, comment out to keep quiet
  //GPS.sendCommand(PGCMD_NOANTENNA);
  delay(2000);
  //mySerial.println(PMTK_Q_RELEASE);

  //idle until button press (held for 1 second)
  uint8_t bpress=0;
  while (!bpress){
    if (digitalRead(STRTB)==HIGH){
      delay(1000);
      if (digitalRead(STRTB)==HIGH){
        bpress=1;
      }
    }
  }

  // blink to indicate user input for logging
  for (uint8_t j=0; j<5; j++){
    digitalWrite(STAT,HIGH);
    delay(400);
    digitalWrite(STAT,LOW);
    delay(400);
  }

  // check for TC malfunction
  if (isnan(thermocouple.readCelsius())) noTC();

  // dont start logging until GPS is up and running
  // not sure why needed yet, but keeps things more tidy
  while (!GPS.newNMEAreceived()) {
      char c = GPS.read();
  }
  do {
    delay(100);
    while (!GPS.newNMEAreceived()) {
      char c = GPS.read();
    } 
    parset=GPS.parse(GPS.lastNMEA());
  } while (!GPS.fix || !parset);

  //--- initialize time parameters from GPS
  time0 = GPS.hour*36000+GPS.minute*600+10*GPS.seconds - millis()/100;
  year = GPS.year+2000;
  month = GPS.month;
  day = GPS.day;
}

// main loop ------------------------------------------------------------------------------
void loop(void) { 

  logData(); //run the logging loop

}

// Acquire a data record ----------------------------------------------------
void acquireData(data_t* data,uint32_t curTime,uint32_t count) {
  data->t_sec = curTime;
  if (count<=19 && digitalRead(GPS_ENABLE)==HIGH) {
    if (gpslog) {
      do{
        while (!GPS.newNMEAreceived()) {
          char c = GPS.read();
        }
        parset=GPS.parse(GPS.lastNMEA());
      } while (!GPS.fix || !parset);
      data->t_sec = GPS.hour*36000+GPS.minute*600+10*GPS.seconds;
      data->lat = GPS.latitude_fixed;
      data->lon = GPS.longitude_fixed;
      gpslog=false;
    }
    else {
      data->lat = 0;
      data->lon = 0;
      gpslog=true;  
    }
  }
  else {
    if (count>19 && digitalRead(GPS_ENABLE)==HIGH){
      digitalWrite(GPS_ENABLE,LOW);
    }
    data->lat = 0;
    data->lon = 0;
  }
  data->tempC=thermocouple.readCelsius();
  if (isnan(data->tempC)) noTC();

}

// stop and give error flash for a bad TC connection -----------------
void noTC() {
 while (isnan(thermocouple.readCelsius())){
  digitalWrite(STAT,HIGH);
  delay(100);
  digitalWrite(STAT,LOW);
  delay(100);
 }
}

// update the time stamps used for file creation
void upDate() {
 hour=(time0/10+millis()/1000)/3600;
 minute=(time0/10+millis()/1000)/60-hour*60;
 second=(time0/10+millis()/1000)-minute*60-hour*3600;
 // make sure that the hour stamp resets at 24
 uint8_t hcircle=floor(hour/24);
 hour=hour-24*hcircle;
}
