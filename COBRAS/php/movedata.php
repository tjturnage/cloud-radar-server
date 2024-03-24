<?php
//inputs
$folder=$_GET['folder'];
$transpose=$_GET['transpose'];

$out = array();
exec('/usr/bin/python3.6 ../py/movedata.py ' . $folder . ' ' . $transpose,$out); 
#exec('/usr/bin/python ../py/movedata.py ' . $folder .  ' >& /tmp/COBRAS2.log',$out); 
foreach($out as $line) {
    echo $line . PHP_EOL;
}

?>
