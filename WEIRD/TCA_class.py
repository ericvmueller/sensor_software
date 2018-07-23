# TCA9548A I2C multiplexer
# I2C Address: 70 through 77
# Channel: 0 - 7

import smbus

CH_ADD={
   0:0x01,
   1:0x02,
   2:0x04,
   3:0x08,
   4:0x10,
   5:0x20,
   6:0x40,
   7:0x80}

# class for the I2C switch----------------------------------------------------
class I2C_SW(object):
   # init________________________________________________________________________ 
   def __init__(self,address,bus_nr):
      self.address=address
      self.bus_nr=bus_nr
      self.bus=smbus.SMBus(bus_nr)
      self.bus.write_byte(self.address,0x00)

   # Change to i2c channel 0..7__________________________________________________
   def chn(self,channel):
      self.bus.write_byte(self.address,CH_ADD[channel])

# block all channels read only the main I2c ( on which is the address SW)_____
#def _rst(self):
#self.bus.write_byte(self.address,0)
#print self.name,' ','Switch reset'

# read all 8 channels__________________________________________________________
#def _all(self):
#self.bus.write_byte(self.address,0Xff)
#print self.name,' ','Switch read all lines'

