<?php
require 'vendor/autoload.php';

use PhpMqtt\Client\MqttClient;
use PhpMqtt\Client\Exceptions\MqttClientException;


$server   = 'localhost';
$port     = 1883;
$clientId = 'php-mqtt-publisher';
$topic    = 'site/start';
$message  = true;

$mqtt = new MqttClient($server, $port, $clientId);


try {
    $mqtt->connect();
    $mqtt->publish($topic, $message, 0);
    $mqtt->disconnect();
    echo "message start envoyé!\n";
    header("location:" . "retour.php");
} catch (MqttClientException $e) {
    echo "Error: " . $e->getMessage() . "\n";
  
}
?>
