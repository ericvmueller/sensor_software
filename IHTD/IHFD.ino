
/**
 * This program logs data to a binary file.  
 */

#include <Wire.h>
#include <SDP.h>
#include <Adafruit_ADS1015.h>
#include <SPI.h>
#include "SdFat.h"
#include "FreeStack.h"
#include "UserDataType.h"  // Edit this include file to change data_t.
#include "RTClib.h"

// initial reference time from GPS
uint32_t time0;

//==============================================================================
// Start of configuration constants.
//==============================================================================
//Interval between data records in microseconds.
const uint32_t LOG_INTERVAL_USEC = 100000;
//------------------------------------------------------------------------------
// Pin definitions.
//
// SD chip select pin.
const uint8_t SD_CS_PIN = SS;

// status LED
#define STAT 3

//------------------------------------------------------------------------------
// File definitions.
//
// Maximum file size in blocks.
// The program creates a contiguous file with FILE_BLOCK_COUNT 512 byte blocks.
// This file is flash erased using special SD commands.  The file will be
// truncated if logging is stopped early.
// 1hr of logging at 10Hz
const uint32_t FILE_BLOCK_COUNT =  3428;
// log file base name.  Must be six characters or less.
#define FILE_BASE_NAME "HF1_"

// The logger will use SdFat's buffer 
//------------------------------------------------------------------------------
#ifndef RAMEND
// Assume ARM. Use total of nine 512 byte buffers.
const uint8_t BUFFER_BLOCK_COUNT = 8;

#elif RAMEND < 0X8FF
#error Too little SRAM
//
#elif RAMEND < 0X10FF
// Use total of two 512 byte buffers.
const uint8_t BUFFER_BLOCK_COUNT = 1;
//
#elif RAMEND < 0X20FF
// Use total of five 512 byte buffers.
const uint8_t BUFFER_BLOCK_COUNT = 4;
//
#else  // RAMEND
// Use total of 13 512 byte buffers.
const uint8_t BUFFER_BLOCK_COUNT = 12;
#endif  // RAMEND

#define TCAADDR 0x70
//==============================================================================
// End of configuration constants.
//==============================================================================

RTC_DS3231 rtc;
Adafruit_ADS1115 ads1;
SDP_Controller sdp1;
SDP_Controller sdp2;

// Size of file base name.  Must not be larger than six.
const uint8_t BASE_NAME_SIZE = sizeof(FILE_BASE_NAME) - 1;

SdFat sd;
SdBaseFile binFile;
char binName[13] = FILE_BASE_NAME "00.bin";

// Number of data records in a block.
const uint16_t DATA_DIM = (512 - 4)/sizeof(data_t);
//Compute fill so block size is 512 bytes.  FILL_DIM may be zero.
const uint16_t FILL_DIM = 512 - 4 - DATA_DIM*sizeof(data_t);

struct block_t {
  uint16_t count;
  uint16_t overrun;
  data_t data[DATA_DIM];
  uint8_t fill[FILL_DIM];
};

const uint8_t QUEUE_DIM = BUFFER_BLOCK_COUNT + 2;
block_t* emptyQueue[QUEUE_DIM];
uint8_t emptyHead;
uint8_t emptyTail;

block_t* fullQueue[QUEUE_DIM];
uint8_t fullHead;
uint8_t fullTail;

// Advance queue index.
inline uint8_t queueNext(uint8_t ht) {
  return ht < (QUEUE_DIM - 1) ? ht + 1 : 0;
}

//==============================================================================
// Error messages stored in flash.
#define error(msg) errorFlash(F(msg))
//------------------------------------------------------------------------------
void errorFlash(const __FlashStringHelper* msg) {
  sd.errorPrint(msg);
}
//-------------------------------------------------------------------------
// log data
// max number of blocks to erase per erase call
uint32_t const ERASE_SIZE = 262144L;
void logData() {
  DateTime now;
  uint32_t bgnBlock, endBlock;

// Allocate extra buffer space.
  block_t block[BUFFER_BLOCK_COUNT];
  block_t* curBlock = 0;
  
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
  
  // Create new file.
  binFile.close();
  if (!binFile.createContiguous(sd.vwd(),
                                binName, 512 * FILE_BLOCK_COUNT)) {
    error("createContiguous failed");
  }
  now=rtc.now();
  binFile.timestamp(T_WRITE, now.year(), now.month(), now.day(), now.hour(), now.minute(), now.second());
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
  // Start a multiple block write.
  if (!sd.card()->writeStart(bgnBlock, FILE_BLOCK_COUNT)) {
    error("writeBegin failed");
  }
  // Initialize queues.
  emptyHead = emptyTail = 0;
  fullHead = fullTail = 0;
  
  // Use SdFat buffer for one block.
  emptyQueue[emptyHead] = (block_t*)cache;
  emptyHead = queueNext(emptyHead);

  // Put rest of buffers in the empty queue.
  for (uint8_t i = 0; i < BUFFER_BLOCK_COUNT; i++) {
    emptyQueue[emptyHead] = &block[i];
    emptyHead = queueNext(emptyHead);
  }

  // Wait for Serial Idle.
  Serial.println("logon");
  delay(10);
  uint32_t bn = 0;
  uint32_t t0 = millis();
  uint32_t t1 = t0;
  uint32_t curTime = 0;
  uint32_t ct = 0;
  uint32_t logTime = micros();

  while (1) {
    // Time for next data record.
    logTime += LOG_INTERVAL_USEC;
    
    //if process lags behind, skip a record
    if ((int32_t)(logTime - micros()) < 0) {
      continue;             
    }
    //stalls until desired logging time has been reached
    int32_t delta;
      do {
        delta = micros() - logTime;  
      } while (delta < 0);
      tcaselect(5);
      curTime = time0+millis()/100;
      
   if (curBlock == 0 && emptyTail != emptyHead) {
      curBlock = emptyQueue[emptyTail];
      emptyTail = queueNext(emptyTail);
      curBlock->count = 0;
    }

    acquireData(&curBlock->data[curBlock->count++],curTime,ct++);

    if (curBlock->count == DATA_DIM) {
      fullQueue[fullHead] = curBlock;
      fullHead = queueNext(fullHead);
      curBlock = 0;
    }

    if (fullHead == fullTail) {
      // Exit loop if done.

    } else {
      // Get address of block to write.
      block_t* pBlock = fullQueue[fullTail];
      fullTail = queueNext(fullTail);
      // Write block to SD.
      if (!sd.card()->writeData((uint8_t*)pBlock)) {
        error("write data failed");
      }
      
      // Move block to empty queue.
      emptyQueue[emptyHead] = pBlock;
      emptyHead = queueNext(emptyHead);
      bn++;
      if (bn == FILE_BLOCK_COUNT) {
        // File full so stop
        break;
      }
    }
  }

  if (!sd.card()->writeStop()) {
    error("writeStop failed");
  }

}
//------------------------------------------------------------------------------

//setup... 
void setup(void) {

  pinMode(STAT,OUTPUT);
  digitalWrite(STAT,LOW);
  
  Serial.begin(115200);
  while (!Serial) {
    SysCall::yield();
  }
  Serial.println(BUFFER_BLOCK_COUNT);
  if (sizeof(block_t) != 512) {
    error("Invalid block size");
  }

  Wire.begin();
  delay(1000);

  tcaselect(5);
  // initialize the RTC
  while (! rtc.begin()) {
      Serial.println("Couldn't find RTC");
    }
  
    if (rtc.lostPower()) {
      Serial.println("RTC lost power, lets set the time!");
      // following line sets the RTC to the date & time this sketch was compiled
      rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
    }
  
  // initialize ads1115
  tcaselect(0);
  ads1.begin();

  // initialize sdp
  tcaselect(2);
  sdp1.begin();
  sdp1.startContinuousMeasurement(SDP_TEMPCOMP_DIFFERENTIAL_PRESSURE, SDP_AVERAGING_NONE);
  delay(10);
  tcaselect(7);
  sdp2.begin();
  sdp2.startContinuousMeasurement(SDP_TEMPCOMP_DIFFERENTIAL_PRESSURE, SDP_AVERAGING_NONE);
  
  // initialize file system.
  if (!sd.begin(SD_CS_PIN, SPI_FULL_SPEED)) {
    sd.initErrorPrint();
  }
  delay(2000);

  tcaselect(5);
  DateTime now = rtc.now();
  Serial.print(now.hour(), DEC);
  Serial.print(':');
  Serial.print(now.minute(), DEC);
  Serial.print(':');
  Serial.print(now.second(), DEC);
  time0=now.hour()*36000+now.minute()*60+10*now.second() - millis()/100;

}

// main loop ------------------------------------------------------------------------------
void loop(void) { 

  logData(); //run the logging loop

}

// Acquire a data record ----------------------------------------------------
void acquireData(data_t* data, uint32_t curTime, uint32_t count) {
  data->t_sec = curTime;
  tcaselect(0);
  data->TC1 = (1.875e-4)*ads1.readADC_SingleEnded(0);
  data->TC2 = (1.875e-4)*ads1.readADC_SingleEnded(1);
  data->TC3 = (1.875e-4)*ads1.readADC_SingleEnded(2);
  
  tcaselect(2);
  data->DP1 = sdp1.getDiffPressure();
  
  tcaselect(7);
  data->DP2 = sdp2.getDiffPressure();
  
  if (count % 20 == 0){
    Serial.println(curTime);
    Serial.println(data->DP1);
    Serial.println(data->DP2);
    digitalWrite(STAT,HIGH);
    delay(10);
    digitalWrite(STAT,LOW);
  }
}

void tcaselect(uint8_t i) {
  if (i > 7) return;
  Wire.beginTransmission(TCAADDR);
  Wire.write(1 << i);
  Wire.endTransmission();
}

//void upDate() {
// hour=(time0/10+millis()/1000)/3600;
// minute=(time0/10+millis()/1000)/60-hour*60;
// second=(time0/10+millis()/1000)-minute*60-hour*3600;
// // make sure that the hour stamp resets at 24
// uint8_t hcircle=floor(hour/24);
// hour=hour-24*hcircle;
// if (hcircle>0){
//  day++;
// }
//}
