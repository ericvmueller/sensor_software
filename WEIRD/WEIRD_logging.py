
#command line program for logging data from Pi-based WEIRD sensors - e.g. 
#SDP810-125

from yoctopuce.yocto_api import *
from yoctopuce.yocto_currentloopoutput import *
import time
import sys
import numpy as np
#from smbus2 import SMBusWrapper
import smbus
import os.path
import Adafruit_ADS1x15
from datetime import datetime
from SDP8x_class import SDP8x
from TCA_class import I2C_SW

def mean_dp(channel,av_time):
   SW.chn(channel)
   sdp[channel].getDP()
   mean=0.0
   num=int(av_time/0.1)
   for i in range(num-1):
      mean=mean+sdp[channel].DP
      time.sleep(0.1)
   if mean==0:
      mean=0.0001;
   return mean/float(num)

# PID coefficients
KP=1.5
KI=1.0
KD=0.1

# initialize Yoctopuse current controller
YoctoTrue=False
errmsg = YRefParam()
if YAPI.RegisterHub("usb",errmsg) == YAPI.SUCCESS:
   # initialize current loop
   loop = YCurrentLoopOutput.FindCurrentLoopOutput("TX420MA1-CE83F.currentLoopOutput")
   if (loop is not None):
         mod = YModule.FindModule("TX420MA1-CE83F")
         loop.set_current(5.0)
         YoctoTrue=True

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
#      print i
#      if i==3:
#         continue
      SW.chn(i)
      tmp=SDP8x()
      sdp.append(tmp)

# assumed polynomial (open tunnel)
PK=np.array([2.867,-10.43,32.86])
U_MEAN=np.array([0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0])
FQ=np.array([0.0,10.0,20.0,30.0,40.0,50.0,60.0,70.0,80.0])

if os.path.isfile('poly.coef'):
   PK=np.loadtxt('poly.coef')
else:
   np.savetxt('poly.coef',PK)

# program loop
while(1):
   print("\n...please select operation:")
   print("   (S)ensor check")
   print("   (F)requency sweep")
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

   elif UI.lower()=='f':
      # initialize Yoctopuse current controller (if not already)
      if (not YoctoTrue):
         if YAPI.RegisterHub("usb",errmsg) == YAPI.SUCCESS:
            # initialize current loop
            loop = YCurrentLoopOutput.FindCurrentLoopOutput("TX420MA1-CE83F.currentLoopOutput")
            if (loop is not None):
                  mod = YModule.FindModule("TX420MA1-CE83F")
                  loop.set_current(5.0)
                  YoctoTrue=True

      if (not YoctoTrue):
         print("\nERROR: unable to initialize control module - please check connections and switches")
      else:
         print("\nReference probe channel:")
         UI=raw_input("---> ")
         seti=int(UI)
         for i in range(8):
            cur_set=4.0+0.2*FQ[i+1]
            loop.set_current(cur_set)
            time.sleep(4.0)
            dp=mean_dp(seti,30)
            U_MEAN[i+1]=(2.0*abs(dp)/1.223)**(0.5)*0.87
            print U_MEAN
         loop.set_current(5.0)
         M=np.column_stack((FQ**3,FQ**2,FQ,))
         PK=np.linalg.lstsq(M,U_MEAN)[0]
         #PK=np.polyfit(U_MEAN,FQ,3)
         print('\nPolynomial: f={0:.4f}*u^3+{1:.4f}*u^2+{2:.4f}*u'
            .format(PK[0],PK[1],PK[2]))
         np.savetxt('poly.coef',PK)

   elif UI.lower()=='v':
      # initialize Yoctopuse current controller (if not already)
      if (not YoctoTrue):
         if YAPI.RegisterHub("usb",errmsg) == YAPI.SUCCESS:
            # initialize current loop
            loop = YCurrentLoopOutput.FindCurrentLoopOutput("TX420MA1-CE83F.currentLoopOutput")
            if (loop is not None):
                  mod = YModule.FindModule("TX420MA1-CE83F")
                  loop.set_current(5.0)
                  YoctoTrue=True

      if (not YoctoTrue):
         print("\nERROR: unable to initialize control module - please check connections and switches")
      else:
         print("\nReference probe channel:")
         UI=raw_input("---> ")
         seti=int(UI)

         print("\nVelocity set-point [m/s]:")
         UI=raw_input("---> ")
         v_set=float(UI)
         dp_set=(v_set/0.87)**(2.0)*1.223/2.0

         print("\nUse polynomial fit (y/n):")
         UI=raw_input("---> ")
         if (UI.lower()=='y'):
            zero=np.roots(np.concatenate([PK,np.array([-v_set])]))
            fq_set=max(zero[np.where((zero>=0)&(zero<=80))])
            print fq_set
            cur_set=4.0+0.2*fq_set
            loop.set_current(cur_set)
            time.sleep(4.0)
            dp_cur=mean_dp(seti,4)
            v_cur=(2.0*abs(dp_cur)/1.223)**(0.5)*0.87
            print('Current Velocity: {0:.3f} [m/s]'.format(v_cur))

         elif (UI.lower()=='n'):
            dp_cur=mean_dp(seti,2)
            dp_err=(dp_set-dp_cur)
            t_adj=0
            int_err=0
            dt_err=0
            match=0
            while (match<3):
               dp_mod=KP*dp_err+KI*int_err+KD*dt_err
               cur_set=dp_mod*2.0+loop.get_current()
               if (cur_set<4.0):
                  cur_set=4.0
               elif (cur_set>20.0):
                  cur_set=20.0
               loop.set_current(cur_set)
               # time to change fan based on accel/deccl rates
               if (dp_mod>0):
                  rate=5.0/100.0
               else:
                  rate=10.0/100.0
               dt=abs(dp_mod)*0.4*rate+1.0
               print dp_err,dp_mod,cur_set,loop.get_current()
               time.sleep(dt)
               #cur_cur=loop.get_current()
               dp_cur=mean_dp(seti,2)
               v_cur=(2.0*abs(dp_cur)/1.223)**(0.5)*0.87
               print('Current Velocity: {0:.3f} [m/s]'.format(v_cur))
               dp_errn=(dp_set-dp_cur)
               #delta_err=(dp_errn-dp_err)
               int_err=int_err+(dp_errn+dp_err)/2.0*dt
               dt_err=(dp_errn-dp_err)/dt
               dp_err=dp_errn
               if (abs(dp_err/dp_cur)<0.05):
                  match=match+1
               else:
                  match=0

   elif UI.lower()=='l':
      # establish data which will be logged
      if sdp_avail:
         print("\nspecify pressure probe channels to log:")
         UI=raw_input("---> ")
         dpch=map(int, UI.split())
         print dpch

      print("\nspecify loggin interval [ms]:")
      UI=raw_input("---> ")
      LI=int(UI)

      print("\nspecify number of records [-]:")
      UI=raw_input("---> ")
      NR=int(UI)

      print("\nauto series? (y/n):")
      UI=raw_input("---> ")
      if (UI.lower()=='y'):
         AS=1
         print("\nspecify target velocities:")
         UI=raw_input("---> ")
         vel_list=map(float, UI.split())
         print("\nReference probe channel:")
         UI=raw_input("---> ")
         seti=int(UI)
         print("\nfile header?")
         head=raw_input("---> ")
         test_num=len(vel_list)
      else:
         AS=0
         test_num=1
         # open and initialize data output file
         # including header
         fnum=0
         fname="./DATA/"+tinit.strftime("%d_%m_%y")+"_"+str(fnum)+"_dat.csv"
         while os.path.isfile(fname):
            fnum=fnum+1
            fname="./DATA/"+tinit.strftime("%d_%m_%y")+"_"+str(fnum)+"_dat.csv"

         print("\noutput file name? ("+fname+")")
         UI=raw_input("---> ")
         if UI!="":
            fname="./DATA/"+UI

      tinit=datetime.utcnow()
      #### main logging loop ####
      for fn in range(0,test_num):
         if AS==1:
            fname="./DATA/"+head+"_"+str(int(100*vel_list[fn])).zfill(3)+"ms.csv"
            dp_set=(vel_list[fn]/0.87)**(2.0)*1.223/2.0
            zero=np.roots(np.concatenate([PK,np.array([-vel_list[fn]])]))
            fq_set=max(zero[np.where((zero>=0)&(zero<=80))])
            cur_set=4.0+0.2*fq_set
            loop.set_current(cur_set)
            time.sleep(5.0)
            print("\nsetpoint: "+str(vel_list[fn])+" m/s")

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
         print("\n"+fname+" write finished\n")

   elif UI.lower()=="e":
      print "\nExiting...\n"
      exit()
   
   


