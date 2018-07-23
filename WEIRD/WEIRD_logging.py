
#command line program for logging data from Pi-based WEIRD sensors - e.g. SDP810-125

from yocto_api import *
from yocto_currentloopoutput import *
import time
import sys
#from smbus2 import SMBusWrapper
import smbus
import os.path
import Adafruit_ADS1x15
from datetime import datetime
from SDP8x_class import SDP8x
from TCA_class import I2C_SW

def new_set(curdp,setdp):
   delta_dp=(setdp-curdp)/curdp
   # find the 'current current' point
   while (abs(delta_sp)<0.05):
      delta_sp=0.5*delta_dp^2
      # somehow set the new current
      # delay for ramp time
      curdp=mean_dp(seti)
      print (2.0*curdp/1.223)^(0.5)/1.1
      delta_dp=(setdp-curdp)/curdp
   # return the new 

def mean_dp(channel):
   SW.chn(channel)
   sdp[channel].getDP()
   mean=0.0
   for i in range(9):
      mean=mean+sdp[channel].DP
      time.sleep(0.1)
   return mean/10.0

def die(msg):
   sys.exit(msg + " (check USB)")

print("\n!!!! Welcome to the WEIRD data logging software !!!!\n")

# initialize i2c ADC
adc_avail=0
GAIN=16
cv_fac=256/32767.0
DV=[0]*2
dv_ch=[0,3]
if adc_avail:
   adc = Adafruit_ADS1x15.ADS1115()

# initialize SDP sensors, via TCA I2C multiplexer
sdp_avail=1
DPO=[0,0,0,0,0,0]
if sdp_avail:
   sdp=[]
   SW=I2C_SW(0X70, 1)
   time.sleep(.5)
   for i in range(0,6):
      #print i
      SW.chn(i)
      tmp=SDP8x()
      sdp.append(tmp)



# program loop
while(1):
   print("\n...please select operation:")
   print("   (S)ensor check")
   print("   (V)elocity set-point")
   print("   (L)og data")
   print("   (E)xit")

   UI=raw_input("---> ")

   if UI.lower()=="s":
      if adc_avail:
         for i in range(1):
            DV[i]=cv_fac*float(adc.read_adc_difference(3, gain=GAIN,data_rate=8))
            print 'differential {0:d}: {1:.4f}mV'.format(i,DV[i])

      if sdp_avail:
         for i in range(0,6):
            print i
            SW.chn(i)
            #time.sleep(.01)
            sdp[i].getDP()
            print 'DP{0:d}: {1:.2f} Pa'.format(i,sdp[i].DP)

   elif UI.lower()=='v':
      # initialize Yoctopuse current controller
      errmsg = YRefParam()
      if YAPI.RegisterHub("usb",errmsg) != YAPI.SUCCESS:
         sys.exit("init error" + errmsg.value)
      # initialize current loop
      if YCurrentLoopOutput.FirstCurrentLoopOutput() is None:
         die("no module connected")
      loop = YCurrentLoopOutput.FindCurrentLoopOutput("TX420MA1-CE83F.currentLoopOutput")
      mod = YModule.FindModule("TX420MA1-CE83F")
      .set_currentAtStartUp(4.0)
      m.saveToFlash()

      print("\nreference probe channel:")
         UI=raw_input("---> ")
         seti=map(int, UI)
      
      print("\nvelocit set-point [m/s]:")
         UI=raw_input("---> ")
         set_dp=(1.1*float(UI))^(2.0)*1.223/2.0
         cur_dp=mean_dp(seti)
         print (2.0*cur_dp/1.223)^(0.5)/1.1
         dp_err=(set_dp-cur_dp)/cur_dp
         print dp_err
         #cur_cur=loop.get_current()
         #while (abs(dp_err)<0.05):
            #delta_dp=(set_dp-cur_dp)/8.0
            #delta_cur=cur_cur+delta_dp*16.0
            #ramp_time=delta_cur*187.5
            #loop.currentMove(delta_cur,ramp_time)
            #cur_dp=mean_dp(seti)
            #print (2.0*cur_dp/1.223)^(0.5)/1.1
            #dp_err=(set_dp-cur_dp)/cur_dp

   elif UI.lower()=='l':
      # establish data which will be logged
      if sdp_avail:
         print("\nplease specify pressure probe channels to log:")
         UI=raw_input("---> ")
         dpch=map(int, UI.split())
         print dpch

      print("\nplease specify loggin interval [ms]:")
      UI=raw_input("---> ")
      LI=int(UI)

      print("\nplease specify number of records [-]:")
      UI=raw_input("---> ")
      NR=int(UI)

      # open and initialize data output file
      # including header
      tinit=datetime.utcnow()
      fnum=0
      fname="./DATA/"+tinit.strftime("%d_%m_%y")+"_"+str(fnum)+"_dat.csv"
      while os.path.isfile(fname):
         fnum=fnum+1
         fname="./DATA/"+tinit.strftime("%d_%m_%y")+"_"+str(fnum)+"_dat.csv"

      print("\noutput file name? ("+fname+")")
      UI=raw_input("---> ")
      if UI!="":
         fname="./DATA/"+UI

      #### main logging loop ####
      print("\n Writing to: "+fname+"\n")
      dat_file=open(fname,"w+")
      dat_file.write("WEIRD data aquisition\n")
      dat_file.write(tinit.strftime("%d:%m:%y,%H:%M:%S\n"))
      dat_file.write("time [s],record [-],"
         "DV1 [mV],DV2 [mV],DP0 [Pa],DP1 [mV],DP2 [mV],DP3 [pa],"
         "DP4 [Pa],DP5 [Pa]\n")

      count=1
      tstart=int(round(time.time()*1000))
      tlog=tstart+LI
      while(count<NR+1):

         while (int(round(time.time()*1000))-tlog < 0):
            time.sleep(0.001)
         tcur=(int(round(time.time()*1000))-tstart)

         # obtain pressure data
         if sdp_avail:
            for i in dpch:
               SW.chn(i)
               sdp[i].getDP()
               DPO[i]=sdp[i].DP

         # obtain voltage data
         if adc_avail:
            for i in range(1):
               DV[i]=cv_fac*adc.read_adc_difference(3, gain=GAIN, data_rate=8)

         # screen output
         if count%10==0:
            print("Record: "+str(count))
         #time and record
         dat_file.write('{0:.3f},'.format(tcur/1000.0))
         dat_file.write('{0:d},'.format(count))
         dat_file.write('{0:.3f},{1:.3f},'.format(DV[0],DV[1]))
         dat_file.write('{0:.3f},{1:.3f},{2:.3f},{3:.3f},{4:.3f},'
            '{5:.3f}'.format(DPO[0],DPO[1],DPO[2],DPO[3],DPO[4],DPO[5]))
         dat_file.write("\n")
         count=count+1
         tlog=tlog+LI

      dat_file.close()

   elif UI.lower()=="e":
      print "\nExiting...\n"
      exit()
   
   


