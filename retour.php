<?php
// Activer l'affichage des erreurs pour le débogage
error_reporting(E_ALL);
ini_set('display_errors', 1);

// Fonction de log personnalisée
function debug_log($message) {
    error_log($message);
    echo "<!-- Debug: " . htmlspecialchars($message) . " -->\n";
}

debug_log("Starting MQTT process...");

// Vérifier si le fichier phpMQTT.php existe
if (!file_exists("phpMQTT.php")) {
    debug_log("Error: phpMQTT.php file is missing!");
    die("Configuration error: Missing required files");
}

require("phpMQTT.php");

$server = "10.0.200.7";
$port = 1883;
$username = "";
$password = "";
$client_id = "phpMQTT-simon-start-" . uniqid();

// Vérifier si nous avons reçu la difficulté
if (isset($_POST['difficulty'])) {
    $difficulty = $_POST['difficulty'];
    debug_log("Received difficulty: " . $difficulty);

    // Map difficulty to numeric value
    $difficulty_map = [
        'easy' => 0,
        'medium' => 1,
        'hard' => 2
    ];

    if (isset($difficulty_map[$difficulty])) {
        try {
            $mqtt = new phpMQTT($server, $port, $client_id);
            
            if ($mqtt->connect(true, NULL, $username, $password)) {
                debug_log("Successfully connected to MQTT broker");
                
                // First send the difficulty
                $difficulty_message = json_encode(['dif' => $difficulty_map[$difficulty]]);
                $mqtt->publish("site/difficulte", $difficulty_message, 0);
                debug_log("Published difficulty message: " . $difficulty_message);
                
                // Small delay to ensure messages are sent in order
                usleep(100000); // 100ms delay
                
                // Then send the start signal
                $mqtt->publish("site/start", "true", 0);
                debug_log("Published start signal");
                
                $mqtt->close();
                debug_log("MQTT connection closed successfully");
            } else {
                debug_log("Failed to connect to MQTT broker!");
            }
        } catch (Exception $e) {
            debug_log("MQTT Error: " . $e->getMessage());
        }
    } else {
        debug_log("Error: Invalid difficulty value: " . $difficulty);
    }
} else {
    debug_log("Error: No difficulty level received!");
}
?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Page de Jeu</title>
    <style>
        /* Votre CSS existant reste inchangé */
        :root {
            --simon-green: #00cc66;
            --simon-red: #ff3333;
            --simon-yellow: #ffcc00;
            --simon-blue: #3399ff;
            --dark: #1a1a2e;
            --light: #f6f6f6;
            --spacing-md: clamp(1rem, 2vw, 2rem);
            --radius: 15px;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            min-height: 100vh;
            min-height: -webkit-fill-available;
            background-color: var(--dark);
            color: var(--light);
            overflow-x: hidden;
            position: relative;
        }

        .container {
            width: min(95%, 1200px);
            margin: 0 auto;
            padding: var(--spacing-md);
            min-height: 100vh;
            min-height: -webkit-fill-available;
            display: flex;
            flex-direction: column;
            gap: var(--spacing-md);
            position: relative;
            z-index: 1;
        }

        .game-header {
            text-align: center;
            padding: clamp(1rem, 3vh, 3rem) 0;
        }

        .game-title {
            font-size: clamp(2.5rem, 8vw, 4.5rem);
            text-transform: uppercase;
            letter-spacing: 4px;
            background: linear-gradient(45deg, 
                var(--simon-green) 20%, 
                var(--simon-blue) 40%, 
                var(--simon-yellow) 60%, 
                var(--simon-red) 80%);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            filter: drop-shadow(0 0 15px rgba(255,255,255,0.3));
        }

        .btn-primary {
            width: 100%;
            padding: clamp(0.8rem, 2vw, 1.2rem);
            border-radius: var(--radius);
            background: linear-gradient(45deg, var(--simon-green), var(--simon-blue));
            border: none;
            color: white;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-size: clamp(0.9rem, 2vw, 1.1rem);
            cursor: pointer;
            transition: transform 0.3s ease;
            text-decoration: none;
            display: inline-block;
            text-align: center;
        }

        .panel {
            background: rgba(26, 26, 46, 0.95);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-radius: var(--radius);
            padding: clamp(1rem, 3vw, 2.5rem);
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .control-panel {
            border: 2px solid var(--simon-blue);
            box-shadow: 0 0 30px rgba(51, 153, 255, 0.2);
        }

        /* Ajout des styles pour les messages de débogage */
        .debug-messages {
            margin-top: 20px;
            padding: 10px;
            background: rgba(0, 0, 0, 0.5);
            border-radius: var(--radius);
            font-family: monospace;
            white-space: pre-wrap;
            display: none; /* Caché par défaut */
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="game-header">
            <h1 class="game-title">Page de Jeu</h1>
        </header>

        <main class="game-panel">
            <div class="control-panel panel">
                <h2>Le jeu a été lancé</h2>
                <a href="simon.php" class="btn-primary">Retour au jeu</a>
            </div>
        </main>
    </div>

    <?php if (isset($_GET['debug'])): ?>
    <div class="debug-messages">
        <?php
        // Afficher les messages de débogage si ?debug est présent dans l'URL
        echo "Debug Messages:\n";
        if (isset($_POST['difficulty'])) {
            echo "Difficulty: " . htmlspecialchars($_POST['difficulty']) . "\n";
        }
        ?>
    </div>
    <?php endif; ?>
</body>
</html>
