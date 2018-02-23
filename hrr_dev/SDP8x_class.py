import smbus
import time

class SDP8x():
	
   ####communication parameters####
   SDADDRESS = 0x25
   STOP_CONTINUOUS = [0x3F,0xF9]
   RESET = [0x00,0x06]
   START_CONTINUOUS_DP_NOAV = [0x36,0x1E]
   ####scale factors
   SCF = 240.0
   #################################

   #start communication, reset device, and start continuous mode
   def __init__(self):
      self.SDP = smbus.SMBus(1)
      #self.SDP.write_i2c_block_data(0x25,0x3F,[0xF9])
      self.SDP.write_i2c_block_data(SDP8x.SDADDRESS,SDP8x.STOP_CONTINUOUS[0],[SDP8x.STOP_CONTINUOUS[1]])
      time.sleep(.2)
      self.SDP.write_i2c_block_data(SDP8x.RESET[0],SDP8x.RESET[1],[])
      time.sleep(.2)
      self.SDP.write_i2c_block_data(SDP8x.SDADDRESS,SDP8x.START_CONTINUOUS_DP_NOAV[0],[SDP8x.START_CONTINUOUS_DP_NOAV[1]])
      time.sleep(.2)

   #aquire compensated data from the device
   def getDP(self):
      #read data into buffer
      dbuff = self.SDP.read_i2c_block_data(SDP8x.SDADDRESS,0,9)
      #16-bit output
      v_int = (dbuff[0]<<8|dbuff[1])
      #make int signed
      if v_int > 32767:
         v_int = v_int - 65534
      self.DP = v_int/SDP8x.SCF


