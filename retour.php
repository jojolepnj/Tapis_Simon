<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);

function debug_log($message) {
    error_log($message);
    echo "<!-- Debug: " . htmlspecialchars($message) . " -->\n";
}

require("phpMQTT.php");

$server = "10.0.200.7";
$port = 1883;
$client_id = "phpMQTT-simon-" . uniqid();

// Récupérer la langue sélectionnée, par défaut 'fr'
$selected_language = isset($_POST['selected_language']) ? $_POST['selected_language'] : 'fr';

if (isset($_POST['difficulty'])) {
    $difficulty = $_POST['difficulty'];
    
    // Map difficulty to numeric value
    $difficulty_map = [
        'easy' => 0,
        'medium' => 1,
        'hard' => 2
    ];

    try {
        debug_log("Tentative de connexion au broker MQTT ($server:$port)...");
        
        $mqtt = new phpMQTT($server, $port, $client_id);
        
        if ($mqtt->connect(true, NULL, "", "")) {
            debug_log("Connexion MQTT réussie");
            
            // Envoi du message de difficulté
            $difficulty_message = json_encode(['dif' => $difficulty_map[$difficulty]]);
            if ($mqtt->publish("site/difficulte", $difficulty_message, 0)) {
                debug_log("Message de difficulté envoyé: $difficulty_message");
            }
            
            // Attente courte
            usleep(500000); // 500ms
            
            // Envoi du signal de démarrage
            if ($mqtt->publish("site/start", "true", 0)) {
                debug_log("Signal de démarrage envoyé");
            }
            
            $mqtt->close();
            debug_log("Connexion MQTT fermée");
        } else {
            debug_log("ERREUR: Impossible de se connecter au broker MQTT");
        }
    } catch (Exception $e) {
        debug_log("ERREUR MQTT: " . $e->getMessage());
    }
}
?>
<!DOCTYPE html>
<html lang="<?php echo htmlspecialchars($selected_language); ?>">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title data-translate="title">Page de Jeu</title>
    <style>
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

        .language-selector {
            position: fixed;
            bottom: clamp(10px, 2vw, 20px);
            right: clamp(10px, 2vw, 20px);
            z-index: 1000;
        }

        .language-selector select {
            padding: clamp(6px, 1.5vw, 10px) clamp(8px, 2vw, 15px);
            border-radius: var(--radius);
            background: rgba(26, 26, 46, 0.95);
            border: 2px solid var(--simon-yellow);
            color: var(--light);
            font-size: clamp(0.8rem, 2vw, 1rem);
            cursor: pointer;
            backdrop-filter: blur(5px);
            -webkit-backdrop-filter: blur(5px);
        }

        .debug-messages {
            margin-top: 20px;
            padding: 10px;
            background: rgba(0, 0, 0, 0.5);
            border-radius: var(--radius);
            font-family: monospace;
            white-space: pre-wrap;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="game-header">
            <h1 class="game-title" data-translate="title">Page de Jeu</h1>
        </header>

        <main class="game-panel">
            <div class="control-panel panel">
                <h2 data-translate="game_launched">Le jeu a été lancé</h2>
                <a href="simon.php" class="btn-primary" data-translate="return_to_game">Retour au jeu</a>
            </div>
        </main>

        <footer>
            <span data-translate="footer">© 2025 Simon Game - Testez votre mémoire</span>
        </footer>

        <div class="language-selector">
            <select id="languageSelect" onchange="changeLanguage(this.value)">
                <option value="fr">&#x1F1EB;&#x1F1F7; Français</option>
                <option value="en">&#x1F1EC;&#x1F1E7; English</option>
                <option value="de">&#x1F1E9;&#x1F1EA; Deutsch</option>
            </select>
        </div>
    </div>

    <script>
    const translations = {
        en: {
            title: "Game Page",
            game_launched: "The game has been launched",
            return_to_game: "Return to game",
            footer: "© 2025 Simon Game - Test your memory skills"
        },
        fr: {
            title: "Page de Jeu",
            game_launched: "Le jeu a été lancé",
            return_to_game: "Retour au jeu",
            footer: "© 2025 Simon Game - Testez votre mémoire"
        },
        de: {
            title: "Spielseite",
            game_launched: "Das Spiel wurde gestartet",
            return_to_game: "Zurück zum Spiel",
            footer: "© 2025 Simon Spiel - Testen Sie Ihr Gedächtnis"
        }
    };

    document.addEventListener('DOMContentLoaded', function() {
        // Utiliser la langue transmise par le formulaire
        const selectedLang = "<?php echo $selected_language; ?>";
        document.getElementById('languageSelect').value = selectedLang;
        changeLanguage(selectedLang);
    });

    function changeLanguage(lang) {
        document.documentElement.lang = lang;
        const elements = document.querySelectorAll('[data-translate]');
        elements.forEach(element => {
            const key = element.getAttribute('data-translate');
            if (translations[lang] && translations[lang][key]) {
                if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                    element.placeholder = translations[lang][key];
                } else {
                    element.textContent = translations[lang][key];
                }
            }
        });
    }
    </script>

    <?php if (isset($_GET['debug'])): ?>
    <div class="debug-messages">
        <?php
        // Afficher les messages de débogage si ?debug est présent dans l'URL
        echo "Debug Messages:\n";
        if (isset($_POST['difficulty'])) {
            echo "Difficulty: " . htmlspecialchars($_POST['difficulty']) . "\n";
        }
        echo "Selected Language: " . htmlspecialchars($selected_language);
        ?>
    </div>
    <?php endif; ?>
</body>
</html>
