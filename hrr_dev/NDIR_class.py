import serial
import array
import time
from sys import getsizeof

class NDIR7911():
	
   ####communication parameters####
   RESET = [0x02,0x30,0xE3,0xD0]
   BENCH_DATA = [0x02,0x3D,0xE3,0xDD]
   COMPENSATED_DATA = [0x02,0x31,0xE3,0xD1]
   ZERO = [0x02,0x35,0xE3,0xD5]
   Span_Bench = [0x02,0x36,0x80,0x8c,0x90,0x90,0x90,0x90,0x90,0x90,0x90,0x90,0x90,0x90,0x90,0x92,0x90,0x90,
   0x90,0x90,0x90,0x90,0x90,0x90,0xF4,0xD6]
   NIB_MASK=15
   WORD_PREFIX=144
   CO2Conc=8.5
   COConc=0.8
   hexaneConc=0
   propaneConc=0
   NOxConc=0
   #################################

   #establish serial connection
   def __init__(self):
      self.conn=0
      print "\nConnecting to device..."
      self.scon=serial.Serial(port="/dev/ttyUSB0",
         baudrate=9600,
         stopbits=1,
         bytesize=8,
         parity='N',
         timeout=0.25)
      self.scon.write(bytearray(NDIR7911.RESET))
      time.sleep(5)
      self.scon.flushInput()
      self.scon.write(bytearray(NDIR7911.BENCH_DATA))
      time.sleep(1)
      rbuff=self.scon.readall()
      self.scon.flushInput()
      if len(rbuff)>40:
         print "Connected to S/N: ",rbuff[4:11],"\n"
         self.conn=1
      else :
         print "Unable to connect to device\n"
         self.conn=0

   #aquire compensated data from the device
   def compdat(self):
      #send/recieve
      self.scon.write(bytearray(NDIR7911.COMPENSATED_DATA))
      time.sleep(.2)
      rbuff=self.scon.readall()
      self.scon.flushInput()
      #parse input
      co21=ord(rbuff[10])&NDIR7911.NIB_MASK
      co22=ord(rbuff[11])&NDIR7911.NIB_MASK
      co23=ord(rbuff[12])&NDIR7911.NIB_MASK
      co24=ord(rbuff[13])&NDIR7911.NIB_MASK
      co21n=co21<<12
      co22n=co22<<8
      co23n=co23<<4
      self.CO2=(co21n|co22n|co23n|co24)

      co1=ord(rbuff[14])&NDIR7911.NIB_MASK
      co2=ord(rbuff[15])&NDIR7911.NIB_MASK
      co3=ord(rbuff[16])&NDIR7911.NIB_MASK
      co4=ord(rbuff[17])&NDIR7911.NIB_MASK
      co1n=co1<<12
      co2n=co2<<8
      co3n=co3<<4
      self.CO=(co1n|co2n|co3n|co4)

      o21=ord(rbuff[18])&NDIR7911.NIB_MASK
      o22=ord(rbuff[19])&NDIR7911.NIB_MASK
      o23=ord(rbuff[20])&NDIR7911.NIB_MASK
      o24=ord(rbuff[21])&NDIR7911.NIB_MASK
      o21n=o21<<12
      o22n=o22<<8
      o23n=o23<<4
      self.O2=(o21n|o22n|o23n|o24)

   #zero CO/CO2 using room air, spans O2
   def zero(self):
      #send/recieve
      self.scon.write(bytearray(NDIR7911.ZERO))
      time.sleep(1)
      rbuff=self.scon.readall()
      self.scon.flushInput()

