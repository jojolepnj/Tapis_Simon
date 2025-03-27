<?php

require 'vendor/autoload.php';

use PhpMqtt\Client\MqttClient;
use PhpMqtt\Client\Exceptions\MqttClientException;


$server   = 'localhost';
$port     = 1883;
$clientId = 'php-mqtt-subscriber';
$topic    = 'test/topic';


$mqtt = new MqttClient($server, $port, $clientId);
echo "client créé    ";

try {
    $mqtt->connect();
    $mqtt->subscribe($topic, function ($topic, $message) {
        echo "Received message on topic {$topic}: {$message}\n";
    }, 0);

    $mqtt->loop(true);
} catch (MqttClientException $e) {
    echo "Error: " . $e->getMessage() . "\n";
}
?>
