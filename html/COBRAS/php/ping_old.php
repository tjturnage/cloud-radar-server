<?php
#inputs
$folder=$_GET['folder'];
$dir='../data/' . $folder;
$file=$dir . '/timectl.py';
if (!file_exists($dir)) {
   mkdir($dir, 0777, true);
}
if (touch($file)){
echo $file . ' modification time has been changed to present time';
}
else{
echo 'Sorry, could not change modification time of ' . $file;
}
?>
