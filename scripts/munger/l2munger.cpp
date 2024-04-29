//
// Level II archive file munger
// see README.md for more details
// see LICENSE.txt for license
// 

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>



typedef char  int8;
typedef short int16;
typedef int  int32;

typedef unsigned char  uint8 ;
typedef unsigned short uint16;
typedef unsigned int  uint32;



//******************************************************************************
//******************************************************************************
//******************************************************************************

static inline void Swap2( void *aa )
 {
  uint8 *a, b;

  a = (uint8 *)aa;

  b    = a[0];
  a[0] = a[1];
  a[1] = b;
 }


//******************************************************************************

static inline void Swap4( void *aa )
 {
  uint8 *a, b;

  a = (uint8 *)aa;

  b    = a[0];
  a[0] = a[3];
  a[3] = b;
  b    = a[1];
  a[1] = a[2];
  a[2] = b;
 }


//******************************************************************************

time_t W88TimeToTime( uint16 w88_days, uint32 w88_seconds )
 {
  return (time_t)( uint32(w88_days-1) * 86400 + w88_seconds/1000 );
 }


//******************************************************************************

void TimeToW88Time( uint16 &w88_days, uint32 &w88_seconds, time_t seconds )
 {
  w88_days    = (uint16)( (uint32)seconds / 86400 );
  w88_seconds = 1000 * ( (uint32)seconds - 86400 * w88_days );
  w88_days    += 1;
 }


//******************************************************************************
//******************************************************************************
//******************************************************************************

#pragma pack(1)



struct FileHeader
 {
  char   szFilename[12];
  uint32 volumeScanDate;
  uint32 volumeScanTime;
  uint8  radarId[4];

  void Swap()
   {
    Swap4( &volumeScanDate );
    Swap4( &volumeScanTime );
   }
 };


//******************************************************************************

struct PacketHeader
 {
  uint32 ctm[3];
  uint16 nHalfWords;
  uint8  rdaChannel;
  uint8  msgType;
  uint16 sequenceNumber;
  uint16 packetDate;
  uint32 packetTime;
  uint16 nSegments;
  uint16 segmentNumber;

  void Swap()
   {
    Swap2( &nHalfWords );
    Swap2( &sequenceNumber );
    Swap2( &packetDate );
    Swap4( &packetTime );
    Swap2( &nSegments );
    Swap2( &segmentNumber );
   }
 };


//******************************************************************************

struct RadialDataPacket
 {
  uint32 radialTime;
  uint16 radialDate;
  uint16 range;
  uint16 azimuthAngle;
  uint16 azimuthNumber;
  uint16 radialStatus;
  uint16 elevationAngle;
  uint16 elevationNumber;
  int16  reflectivityRange;
  int16  dopplerRange;
  uint16 reflectivityGateSize;
  uint16 dopplerGateSize;
  uint16 reflectivityBins;
  uint16 dopplerBins;
  uint16 cutSectorNumber;
  uint32 calibrationConstant;
  uint16 reflectivityOffset;
  uint16 velocityOffset;
  uint16 spectralWidthOffset;
  uint16 dopplerResolution;
  uint16 vcp;
  uint32 vv;
  uint32 vv2;
  uint16 a2reflectivity;
  uint16 a2velocity;
  uint16 a2spectral;
  uint16 nyquistVelocity;
  int16  atmosAttenuation;
  int16  overlayThreshold;
  uint16 spotBlankingStatus;

  void Swap()
   {
    Swap4( &radialTime );
    Swap2( &radialDate );
    Swap2( &range );
    Swap2( &azimuthAngle );
    Swap2( &azimuthNumber );
    Swap2( &radialStatus );
    Swap2( &elevationAngle );
    Swap2( &elevationNumber ); 
    Swap2( &reflectivityRange );
    Swap2( &dopplerRange );
    Swap2( &reflectivityGateSize );
    Swap2( &dopplerGateSize );
    Swap2( &reflectivityBins );
    Swap2( &dopplerBins );
    Swap2( &cutSectorNumber );
    Swap4( &calibrationConstant );
    Swap2( &reflectivityOffset );
    Swap2( &velocityOffset );
    Swap2( &spectralWidthOffset );
    Swap2( &dopplerResolution );
    Swap2( &vcp );
    Swap4( &vv );
    Swap4( &vv2 );
    Swap2( &a2reflectivity );
    Swap2( &a2velocity );
    Swap2( &a2spectral );
    Swap2( &nyquistVelocity );
    Swap2( &atmosAttenuation );
    Swap2( &overlayThreshold );
    Swap2( &spotBlankingStatus );
   }
 };


//******************************************************************************

struct GenericDataPacket
 {
  char   icao[4];
  uint32 radialTime;
  uint16 radialDate;
  uint16 azimuthNumber;
  float  azimuthAngle;
  uint8  compressionType;
  uint8  spare;
  uint16 uncompressedLength;
  uint8  azimuthSpacing;
  uint8  radialStatus;
  uint8  elevationNumber;
  uint8  cutSectorNumber;
  float  elevationAngle;
  uint8  spotBlankingStatus;
  uint8  azimuthIndexingMode;
  uint16 dataBlockCount;
  uint32 dataBlockOffsets[9];

  void Swap()
   {
    Swap4( &radialTime );
    Swap2( &radialDate );
    Swap2( &azimuthNumber );
    Swap4( &azimuthAngle );
    Swap2( &uncompressedLength );
    Swap4( &elevationAngle );
    Swap2( &dataBlockCount );
    for( int i = 0; i < 9; i++ ) Swap4( &dataBlockOffsets[i] );
   }

 };



#pragma pack()



//******************************************************************************
//******************************************************************************
//******************************************************************************

FILE *src;
FILE *dst;


char   szTargetSite[16];
time_t targetVolumeTime;
time_t timeDelta;

time_t volumeTime;
int    speedFactor;


//******************************************************************************

void AdjustW88Time( uint16 &w88_days, uint32 &w88_seconds )
 {
  time_t seconds;
  time_t innerTimeDelta;  

  seconds = W88TimeToTime( w88_days, w88_seconds );

  innerTimeDelta = seconds - volumeTime;

  seconds += timeDelta - innerTimeDelta + (innerTimeDelta / speedFactor);

  TimeToW88Time( w88_days, w88_seconds, seconds );
 }


//******************************************************************************
//******************************************************************************
//******************************************************************************

bool ProcessFileHeader()
 {
  FileHeader fh;



  printf( "ProcessFileHeader:\n" );


  //-------------------------- Read file header --------------------------------

  if( fread( &fh, sizeof(fh), 1, src ) != 1 )
   {
    printf( "*** fread failed!\n" );
    return false;
   }

  fh.Swap();


  //--------------------- Determine time delta from VST ------------------------

  volumeTime = W88TimeToTime( (uint16)fh.volumeScanDate, fh.volumeScanTime );

  timeDelta = targetVolumeTime - volumeTime;

  printf( "  timeDelta = %d seconds\n", timeDelta );


  //----------------------- Adjust output header time --------------------------

  uint16 w88_days;
  uint32 w88_seconds;

  TimeToW88Time( w88_days, w88_seconds, volumeTime+timeDelta );

  fh.volumeScanDate = (uint32)w88_days;
  fh.volumeScanTime = w88_seconds;

  memcpy( fh.radarId, szTargetSite, 4 );


  //------------------------ Swap and write to dest ----------------------------

  fh.Swap();

  fwrite( &fh, sizeof(fh), 1, dst );


  return true;
 }


//******************************************************************************
//******************************************************************************
//******************************************************************************

#define MaxBuffer  ( 64 * 1024 )


//******************************************************************************

bool ProcessPacket()
 {
  PacketHeader ph;
  static uint8 buffer[MaxBuffer];


  //------------------------ Read packet header --------------------------------

  if( fread( &ph, sizeof(ph), 1, src ) != 1 )
   {
//    printf( "*** ProcessPacket: fread( ph ) failed!\n" );   // not an error!
    return false;
   }

  ph.Swap();


  //--------------------------- Read payload -----------------------------------

  int cbPayload;


  if( ph.msgType == 31 )
    {
     cbPayload = 2 * (int)(uint32)ph.nHalfWords - sizeof(PacketHeader) + 12;
    }
   else   // assume everything else is simple 2432 packet
    {
     cbPayload = 2432 - sizeof(PacketHeader);
    }


  if( cbPayload == 0 ) return true;


  if( fread( &buffer, cbPayload, 1, src ) != 1 )
   {
    printf( "*** ProcessPacket: error reading packet payload!\n" );
    return false;
   }


  //----------------------- Munge packet contents ------------------------------

  AdjustW88Time( ph.packetDate, ph.packetTime );

  if( ph.msgType == 1 )
    {
     RadialDataPacket *rdp;

     rdp = (RadialDataPacket *)buffer;
     rdp->Swap();

     AdjustW88Time( rdp->radialDate, rdp->radialTime );

     rdp->Swap();
    }
   else if( ph.msgType == 31 )
    {
     GenericDataPacket *gdp;


     gdp = (GenericDataPacket *)buffer;
     gdp->Swap();

     AdjustW88Time( gdp->radialDate, gdp->radialTime );

     gdp->Swap();
    }


  //---------------------- Write header and payload ----------------------------

  ph.Swap();
  fwrite( &ph, sizeof(ph), 1, dst );


  fwrite( &buffer, cbPayload, 1, dst );


  return true;
 }


//******************************************************************************
//******************************************************************************
//******************************************************************************
//
//              1        2          3     4       5
//  l2munger  SSSS  YYYY/MM/DD  HH:MM:SS  X  source_file
//
//
//

int main( int argc, char *argv[] )
 {
  char szSrc[512];
  char szDst[512];



  if( argc != 6 )
   {
    printf( "Usage: l2munger SSSS  YYYY/MM/DD  HH:MM:SS  X  source_file\n" );
    return 0;
   }


  //----------------------- Process command line -------------------------------

  int rc;
  int year, month, day, hour, minute, second, speed;


  if( strlen( argv[1] ) != 4 )
   {
    printf( "*** error reading new site ID from command line!\n" );
    return 0;
   }

  strcpy( szTargetSite, argv[1] );
  //toupper( szTargetSite );


  rc = sscanf( argv[2], "%4d/%2d/%d", &year, &month, &day );
  if( rc != 3 )
   {
    printf( "*** error reading target date from command line\n" );
    return 0;
   }

  rc = sscanf( argv[3], "%2d:%2d:%d", &hour, &minute, &second );
  if( rc != 3 )
   {
    printf( "*** error reading target time from command line\n" );
    return 0;
   }

  speed = atoi( argv[4] );

  strcpy( szSrc, argv[5] );


  //-------------------- Calculate target volume time --------------------------

  struct tm mt;


  putenv( "TZ=UTC" );
  tzset();


  memset( &mt, 0, sizeof(mt) );

  mt.tm_year = year - 1900;
  mt.tm_mon  = month - 1;
  mt.tm_mday = day;

  mt.tm_hour = hour;
  mt.tm_min  = minute;
  mt.tm_sec  = second;

  targetVolumeTime = mktime( &mt );
  if( targetVolumeTime == (time_t)-1 )
   {
    printf( "*** unable to convert target time and date!\n" );
    return 0;
   }


  speedFactor = speed;



  sprintf( szDst, "%s%.4d%.2d%.2d_%.2d%.2d%.2d", szTargetSite, year, month, day, hour, minute, second );

  printf( "destination file = %s\n", szDst );


  //---------------------------- Open files ------------------------------------

  src = fopen( szSrc, "rb" );
  if( src == 0 )
   {
    printf( "*** fopen( %s ) src failed!\n", szSrc );
    return 0;
   }

  dst = fopen( szDst, "wb" );
  if( dst == 0 )
   {
    printf( "*** fopen( %s ) dst failed!\n", szDst );
    return 0;
   }


  //---------------------- Loop over source file -------------------------------

  if( ProcessFileHeader() )
   {
    while( ProcessPacket() );
   }


  //------------------------- Clean up and exit --------------------------------

  fclose( dst );
  fclose( src );

  return 0;
 }


