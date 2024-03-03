import pandas as pd
import numpy as np
from pathlib import Path
from struct import unpack


print("\ndevice type?")
print("     (1) fire tracker")
print("     (2) understory tower")
device=int(input("---> "))

if device==1:
	prefix='FT'
	data_chunk_count=31
	data_chunk_size=16
	pad_bytes=12
	alias=["time [UTC]","time [s]","lat [deg]","lat [min]","lon [deg]","lon [min]","TC Temp [C]"]
elif device==2:
	prefix='DL'
	data_chunk_count=8
	data_chunk_size=60
	pad_bytes=28
	alias=["time [UTC]","time [s]","lat [deg]","lat [min]","lon [deg]","lon [min]",
	"TC1 Temp [C]",
	"TC2 Temp [C]",
	"TC3 Temp [C]",
	"TC4 Temp [C]",
	"TC5 Temp [C]",
	"TC6 Temp [C]",
	"TC7 Temp [C]",
	"TC8 Temp [C]",
	"TC9 Temp [C]",
	"TC10 Temp [C]",
	"TC11 Temp [C]",
	"TC12 Temp [C]",]
else:
	print("DEVICE NUMBER NOT RECOGNIZED")
	exit()

print("\nfile directory? (./)")
folder=input("---> ")
if folder=="":
	folder="./"

# for now, assume max device number and max file index
for i in range(150):
	for j in range(100):
		if device==1:
			fileName=Path(folder+prefix+"{0:03d}_{1:02d}.bin".format(i,j))
		elif device==2:
			fileName=Path(folder+prefix+"{0:02d}_{1:02d}.bin".format(i,j))
		if fileName.is_file():
			with open(fileName,'rb') as binFile:
				count=0
				time=np.zeros([86500])
				lat=np.zeros([86500])
				lon=np.zeros([86500])
				if device==1:
					TC=np.zeros([86500])
				elif device==2:
					TC=np.zeros([86500,12])
				clock=[]
				print(fileName)
				while (binFile.read(2)):
					binFile.read(2)
					for bi in range(data_chunk_count):
						if device==1:
							data = unpack('<Lllf', binFile.read(data_chunk_size))
							TC[count]=data[3]
						elif device==2:
							data = unpack('<Lllffffffffffff', binFile.read(data_chunk_size))
							for tci in range(12):
								TC[count,tci]=data[3+tci]
						time[count]=data[0]
						lat[count]=data[1]
						lon[count]=data[2]
						
						HH=(time[count]/36000).astype(int)
						MM=(time[count]/600-HH*60).astype(int)
						SS=(time[count]-HH*36000-MM*600)*.1
						clock.append('{0:02d}:{1:02d}:{2:.1f}'.format(HH,MM,SS))
						count+=1

					binFile.read(pad_bytes)

			end_count=np.where(time>0)[0][-1]
			print('total records found: {0}'.format(end_count))
                
			if device==1:
				df=pd.DataFrame({
					"clock" : clock[:end_count],
					"time" : 0.1*time[:end_count],
					"lat_deg" : (lat[:end_count]/10000000).astype(int),
					"lat_min" : np.round(((lat[:end_count]/10000000)%1)*60,5),
					"lon_deg" : (lon[:end_count]/10000000).astype(int),
					"lon_min" : np.round(((lon[:end_count]/10000000)%1)*60,5),
					"TC" : TC[:end_count]
	                })
			elif device==2:
				df=pd.DataFrame({
 					"clock" : clock[:end_count],
 					 "time" : 0.1*time[:end_count],
 					"lat_deg" : (lat[:end_count]/10000000).astype(int),
 					"lat_min" : np.round(((lat[:end_count]/10000000)%1)*60,5),
 					"lon_deg" : (lon[:end_count]/10000000).astype(int),
 					"lon_min" : np.round(((lon[:end_count]/10000000)%1)*60,5),
 					"TC1" : TC[:end_count,0],
 					"TC2" : TC[:end_count,1],
 					"TC3" : TC[:end_count,2],
 					"TC4" : TC[:end_count,3],
 					"TC5" : TC[:end_count,4],
 					"TC6" : TC[:end_count,5],
 					"TC7" : TC[:end_count,6],
 					"TC8" : TC[:end_count,7],
 					"TC9" : TC[:end_count,8],
 					"TC10" : TC[:end_count,9],
 					"TC11" : TC[:end_count,10],
 					"TC12" : TC[:end_count,11],
	                })
			df.to_csv(fileName.name[:-3]+'csv',header=alias,na_rep=np.nan)

