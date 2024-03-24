<?php
//inputs
$startdate=$_GET['startdate'];
$enddate=$_GET['enddate'];
$currentdate=$_GET['currentdate'];
$speed=$_GET['speed'];
$folder=$_GET['folder'];
$dir='../data/' . $folder;
$timectlfile=$dir . '/timectl.py';

if (!file_exists($dir)) {
   mkdir($dir, 0777, true);
}

$handle = fopen($timectlfile,'w') or die ('ERROR: CANNOT OPEN '.$timectlfile);
fwrite($handle,'startdate='.$startdate.PHP_EOL);
fwrite($handle,'enddate='.$enddate.PHP_EOL);
fwrite($handle,'currentdate='.$currentdate.PHP_EOL);
fwrite($handle,'speed='.$speed.PHP_EOL);
fclose($handle);
echo 'Finished Ping' .PHP_EOL;
?>
