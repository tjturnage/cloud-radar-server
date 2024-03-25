<?php
//inputs
$startdate=$_GET['startdate'];
$enddate=$_GET['enddate'];
$currentdate=$_GET['currentdate'];
$speed=$_GET['speed'];
$folder=$_GET['folder'];
$dir='../data/' . $folder;
$timectlfile=$dir . '/timectl.py';

$handle = fopen($timectlfile,'w') or die ('ERROR: CANNOT OPEN '.$timectlfile);
fwrite($handle,'startdate='.$startdate.PHP_EOL);
fwrite($handle,'enddate='.$enddate.PHP_EOL);
fwrite($handle,'currentdate='.$currentdate.PHP_EOL);
fwrite($handle,'speed='.$speed.PHP_EOL);
fclose($handle);

$out = array();
exec('/usr/bin/python ../py/movedata.py ' . $folder,$out); 
#exec('/usr/bin/python ../py/movedata.py ' . $folder .  ' >& /tmp/COBRAS2.log',$out); 
foreach($out as $line) {
    echo $line . PHP_EOL;
}

?>
