<?php
//inputs
$folder=$_GET['folder'];
$statusfile='../data/' . $folder . '/download/status';
if ( file_exists($statusfile)) {
  $contents=file_get_contents($statusfile);
} 
else {
  $contents='0 0 1';
}
echo $contents;
?>
