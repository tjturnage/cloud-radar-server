<?php
//inputs
$folder=$_GET['folder'];
$radarfiles=$_GET['radarfiles'];
$startdatetext=$_GET['startdatetext'];
$enddatetext=$_GET['enddatetext'];
$transpose=$_GET['transpose'];
#echo $folder
$out = array();

echo $folder . ' ' . $radarfiles . ' ' . $startdatetext . ' ' . $enddatetext . ' ' .  $transpose . PHP_EOL;


#exec('/usr/bin/python ../py/startsim.py ' . $folder . ' ' . escapeshellarg(json_encode($radarfiles)) . ' ' . $startdatetext . ' ' . $enddatetext,$out);
exec('/usr/bin/python3.6 ../py/startsim.py ' . $folder . ' ' . escapeshellarg(json_encode($radarfiles)) . ' ' . $startdatetext . ' ' . $enddatetext . ' ' . $transpose . ' >& /tmp/COBRAS2.log',$out);
#exec('/bin/echo GOODBYE >& /tmp/COBRAS2.log');
echo 'Finished downloading' .PHP_EOL;
foreach($out as $line) {
    echo $line . PHP_EOL;
}
?>
