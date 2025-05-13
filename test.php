<?php
// test.php

// Enable error reporting for debugging purposes (remove in production)
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

require_once("config.php");

// Global PDO instance
$pdo = null;

/**
 * Connect to the database.
 */
function bddConnect() {
    global $pdo;
    try {
        $pdo = new PDO(
            "mysql:host=" . SERVER . ";dbname=" . BDD . ";charset=utf8",
            USER,
            PWD,
            array(PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION)
        );
        echo "Database connected successfully.<br>";
    } catch (Exception $e) {
        echo "Connection error: " . $e->getMessage() . "<br>";
        $pdo = null;
        die();
    }
}

/**
 * Insert a new record into the Passage_tag table.
 *
 * @param string $tag The tag to insert.
 * @return bool True on success, false on failure.
 */
function ajoutePassage($tag) {
    global $pdo;
    if ($pdo === null) {
        bddConnect();
    }
    try {
        $sql = "INSERT INTO Passage_tag (tag) VALUES (:tag)";
        $stmt = $pdo->prepare($sql);
        $stmt->bindParam(':tag', $tag);
        $stmt->execute();
        echo "Insert successful.<br>";
        return true;
    } catch (PDOException $e) {
        echo "Database Error: " . $e->getMessage() . "<br>";
        return false;
    }
}

// Process POST requests from Arduino.
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Save POST data to a file
    $data = json_encode($_POST);
    file_put_contents('data.txt', $data);
    echo "POST Received: " . $data . "<br>";

    // Check if the tag parameter exists
    if (isset($_POST['tag'])) {
        $tag = $_POST['tag'];
        echo "Processing tag: " . $tag . "<br>";
        if (ajoutePassage($tag)) {
            echo "Tag inserted successfully.<br>";
        } else {
            echo "Failed to insert tag.<br>";
        }
    } else {
        echo "No tag provided.<br>";
    }
} else {
    // For GET requests, display the last saved POST data
    echo "Last POST Data: " . @file_get_contents('data.txt');
}
?>
