<?php
//inputs
$prefix=$_GET['prefix'];

//for some reason file_get_contents doesn't work on WW servers
//so we must use this function
function url_get_contents ($Url) {
    if (!function_exists('curl_init')){
        die('CURL is not installed!');
    }
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $Url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $output = curl_exec($ch);
    curl_close($ch);
    return $output;
}

//determine if this is the year/month/day folders
//OR
//radar folders
$values = explode("/", $prefix);
$isradar=$values[sizeof($values)-1];

if ( is_numeric($isradar) or $prefix == '' ){
  //Last value in prefix string is numberic, not radar folders (ex: 2017,2009,05,etc)
  $xml_structure1='CommonPrefixes';
  $xml_structure2='Prefix';
}
else{
  //Last value in prefix string is NOT numberic, these are radar folders (ex: KIWA,KYUM)
  $xml_structure1='Contents';
  $xml_structure2='Key';
}

//$prefix=2017;
if ( $prefix == '' ){
  $prefixstring='';
}
else{
  $prefixstring='&prefix=' . $prefix . '/';
}

$map_url='https://noaa-nexrad-level2.s3.amazonaws.com/?delimiter=/' . $prefixstring;
//This command does not work on WW servers 
//$response_xml_data = file_get_contents($map_url);
$response_xml_data = url_get_contents($map_url);
$data = simplexml_load_string($response_xml_data);
$myarray = array();
  foreach ( $data->$xml_structure1 as $result ){
  $value=$result->$xml_structure2;
  //remove the prefix
  $value=str_replace($prefix,"",$value);
  //remove the /'s
  $value=str_replace('/',"",$value);
  array_push($myarray,$value);
  }
echo json_encode($myarray);
?>
