<?php
//inputs
$folder=$_GET['folder'];
$out = array();

$downloadfolder='../data/'.$folder.'/download';
$data=$downloadfolder.'/*_*';
$zipfile=$downloadfolder.'/data.zip';
$zip = new ZipArchive;
if ($zip->open($zipfile, ZipArchive::OVERWRITE) === TRUE)
{
  foreach (glob($data) as $filename) {
    // Add file to the zip file
    $zip->addFile($filename,basename($filename));
  }
}
// All files are added, so close the zip file.
$zip->close();


foreach($out as $line) {
    echo $line . PHP_EOL;
}
?>
