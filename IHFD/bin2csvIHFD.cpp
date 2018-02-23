#include <stdio.h>
#include <string>
#include <stdint.h>
#include <cstdio>
#include <iostream>
using std::string;

FILE *source;
FILE *destination;
char inName[13];
char outName[13];
int count = 0;
int premat = 0;

struct tdat_t {
  uint32_t t_sec;
  float TC1,TC2,TC3;
  float DP1,DP2;
};

inline bool fexists(const std::string& name) {
	if (FILE *file = fopen(name.c_str(), "r")) {
		fclose(file);
		return true;
	}
	else {
		return false;
	}
}

void replaceExt(string& s, const string& newExt) {

	string::size_type i = s.rfind('.', s.length());

	if (i != string::npos) {
		s.replace(i + 1, newExt.length(), newExt);
	}
}

int main() {
  tdat_t tdt;
  uint16_t jnk1;
  uint8_t jnk2;
  float ts;

  // return the filenames of all files that have the specified extension
  // in the current directory

  for (uint8_t ii = 0; ii < 100; ii++){
    for (uint8_t jj = 0; jj < 100; jj++){
      sprintf(inName, "HF%.1d_%.2d.bin", ii, jj);
	  string fil = inName;
	  if (fexists(inName)){
	    sprintf(outName, "HF%.1d_%.2d.csv", ii, jj);
		printf("%s\n",inName);
		
		source = fopen(inName, "rb");
		if (!source) {
		  printf("open failed for %s\n", inName);
		  return 0;
		}
		destination = fopen(outName, "w");
		if (!destination) {
		  printf("open failed for %s\n",outName);
		  return 0;
		}
			  
		fprintf(destination, "time [s],TC1 [C],TC1 [C],TC3 [C],DP1 [Pa],DP2 [Pa]\n");

        while (!feof(source)) {
		  count = 0;
		  premat = 0;
		  fread(&jnk1, sizeof(jnk1), 1, source);
		  fread(&jnk1, sizeof(jnk1), 1, source);
		  while (++count <= 21){
		    if (fread(&tdt, sizeof(tdt), 1, source)){
			  // check to see if we have reached a point where the logging stopped
			  if (tdt.t_sec == 0) {
			    if (premat == 1) {
				  goto exitloop;
				}
			    premat = 1;
			  }
			  ts=(float)tdt.t_sec/10;
			  fprintf(destination, "%.2f,%.4f,%.4f,%.4f,%.4f,%.4f\n", 
			  ts,200.92*tdt.TC1-6.2974,200.92*tdt.TC2-6.2974,200.92*tdt.TC3-6.2974,tdt.DP1,tdt.DP2);
			}
		  }
		  for (uint8_t i=0;i<4;i++){
		  	fread(&jnk2, sizeof(jnk2), 1, source);
		  }
		}
		exitloop:
		fclose(source);
		fclose(destination);
	  }
    }
  }
  return 0;
}


