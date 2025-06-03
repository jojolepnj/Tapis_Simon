<?php
require("phpMQTT.php");

$server = "10.0.200.7";     // MQTT broker address
$port = 1883;               
$username = "";             
$password = "";             
$client_id = "phpMQTT-simon-start-" . uniqid();

// Get the difficulty from the form
$difficulty = isset($_POST['difficulty']) ? $_POST['difficulty'] : '';

// Map difficulty to numeric value
$difficulty_map = [
    'easy' => 0,
    'medium' => 1,
    'hard' => 2
];

$mqtt = new phpMQTT($server, $port, $client_id);

if ($mqtt->connect(true, NULL, $username, $password)) {
    // First send the difficulty
    $difficulty_message = json_encode(['dif' => $difficulty_map[$difficulty]]);
    $mqtt->publish("site/difficulte", $difficulty_message, 0);
    
    // Then send the start signal
    $mqtt->publish("site/start", "true", 0);
    $mqtt->close();
    
    // Redirect back to the game page with success message
    header("Location: simon.php?status=started");
    exit();
} else {
    // Redirect back with error
    header("Location: simon.php?status=error");
    exit();
}
?>
