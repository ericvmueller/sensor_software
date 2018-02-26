#ifndef UserDataType_h
#define UserDataType_h
struct data_t {
  uint32_t t_sec;
  int32_t lat, lon;
  float tempC[12];
};
#endif  // UserDataType_h
