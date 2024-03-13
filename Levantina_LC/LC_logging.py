import serial
import time
from datetime import datetime
import os.path
import sys

print("\n!!!! Welcome to the load cell logging software !!!!\n")

LCC=[]
name=[]

#LC1=serial.serial_for_url('socket://10.0.0.12:10001',timeout=1,baudrate=9600,parity=serial.PARITY_NONE)
#chch=ord('0')^ord('1')^ord('z')
#print(chch)
#LC1.write(b'$01z7B\r')
#buff=LC1.readline()
#print(buff)
#LC1.write(b'$01t75\r')
#buff=LC1.readline()
#print(float(buff[3:9]))

while(1):
   print("\n...please select operation:")
   print("   (A)dd new load cell connection")
   print("   (D)isplay current mass")
   print("   (T)are load cells")
   print("   (L)og data")
   print("   (E)xit")

   UI=input("---> ")

   if UI.lower()=="a":
      print("\nspecify IP address (make sure computer static IP is similar):")
      IP=input("---> ")
      tmp=serial.serial_for_url('socket://'+IP+':10001',timeout=.05,baudrate=9600)
      LCC.append(tmp)
      print("\nspecify name for load cell:")
      LCC[-1].name=input("---> ")
      LCC[-1].mass=-9999

   if UI.lower()=="d":
      if len(LCC) is 0:
         print("\nERROR: No load cells currently connected\n")
      else:
            for i in range(len(LCC)):
               LCC[i].write(b'$01t75\r')
               buff=LCC[i].readline()
               LCC[i].mass=float(buff[3:9])
               print('\n'+LCC[i].name+': '+str(LCC[i].mass)+' g')

   if UI.lower()=="t":
      if len(LCC) is 0:
         print("\nERROR: No load cells currently connected\n")
      else:
            for i in range(len(LCC)):
               LCC[i].write(b'$01z7B\r')
               buff=LCC[i].readline()

   elif UI.lower()=='l':
      
      print("\nspecify loggin interval [ms]:")
      UI=input("---> ")
      LI=int(UI)

      tinit=datetime.utcnow()
      fnum=0
      fname="./DATA/mass_data_"+tinit.strftime("%d_%m_%y")+"_"+str(fnum)+"_dat.csv"
      while os.path.isfile(fname):
         fnum=fnum+1
         fname="./DATA/mass_data_"+tinit.strftime("%d_%m_%y")+"_"+str(fnum)+"_dat.csv"

      print("\noutput file name? ("+fname+")")
      UI=input("---> ")
      if UI!="":
         fname="./DATA/"+UI

      #### main logging loop ####
      print("\n Writing to: "+fname+" in continuous mode ...press ctrl-c to end\n")
      dat_file=open(fname,"w+")
      dat_file.write("load cell data aquisition\n")
      dat_file.write(tinit.strftime("%d:%m:%y,%H:%M:%S\n"))
      dat_file.write("time [s],record [-],")
      for i in range(len(LCC)):
         dat_file.write(LCC[i].name+" [g]")
      dat_file.write("\n")
      count=1
      tstart=int(round(time.time()*1000))
      tlog=tstart+LI
      while(1):
         try:
            while (int(round(time.time()*1000))-tlog < 0):
               time.sleep(0.001)
            tcur=(int(round(time.time()*1000))-tstart)

            # obtain data
            for i in range(len(LCC)):
               LCC[i].write(b'$01t75\r')
               buff=LCC[i].readline()
               LCC[i].mass=float(buff[3:9])

            # screen output
            if count%10==0:
               print("Record: "+str(count))
            
            # file output
            dat_file.write('{0:.3f},'.format(tcur/1000.0))
            dat_file.write('{0:d},'.format(count))
            for i in range(len(LCC)):
               dat_file.write('{0:.1f},'.format(LCC[i].mass))
            dat_file.write("\n")
            count=count+1
            tlog=tlog+LI

         except KeyboardInterrupt:
            dat_file.close()
            print("\n"+fname+" write finished\n")
            break

   elif UI.lower()=="e":
      print("\nExiting...\n")
      exit()


