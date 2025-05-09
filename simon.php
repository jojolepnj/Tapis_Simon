<?php
require('phpMQTT.php'); // Inclure la bibliothèque phpMQTT

// Configuration MQTT
$host = 'localhost'; 
$port = 1883;
$username = '';
$password = '';
$client_id = 'simon_game_' . uniqid();

$message = "";

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['difficulty'])) {
    $difficulty = $_POST['difficulty'];
    $payload = json_encode(["dif" => $difficulty]);

    $mqtt = new phpMQTT($host, $port, $client_id);
    if ($mqtt->connect(true, NULL, $username, $password)) {
        $mqtt->publish('site/difficulte', $payload, 0);
        $mqtt->publish('site/start', 'start', 0);
        $mqtt->close();
        $message = "✅ Difficulté envoyée : $payload";
    } else {
        $message = "❌ Échec de la connexion au serveur MQTT.";
    }
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Simon Game</title>
    <!-- Votre CSS inchangé ici -->
    <style>
        /* ... Styles CSS non modifiés pour gain de place ... */
    </style>
</head>
<body>
    <div class="container">
        <header class="game-header">
            <h1 class="game-title" data-translate="title">Simon</h1>
        </header>

        <main class="game-panel">
            <div class="control-panel panel">
                <h2 data-translate="choose_level">Choose Level</h2>
                <form id="difficulty-form" class="difficulty-form" method="POST">
                    <select class="form-select" name="difficulty" required>
                        <option value="" selected disabled data-translate="select_difficulty">Select difficulty</option>
                        <option value="easy" data-translate="easy">Easy - Normal speed</option>
                        <option value="medium" data-translate="medium">Medium - Fast speed</option>
                        <option value="hard" data-translate="hard">Hard - Very fast speed</option>
                    </select>
                    <button type="submit" class="btn-primary" data-translate="start_game">Start Game</button>
                </form>
                <?php if (!empty($message)): ?>
                    <p><?= htmlspecialchars($message) ?></p>
                <?php endif; ?>
            </div>

            <div class="highscores-panel panel">
                <h2 data-translate="high_scores">High Scores</h2>
                <!-- Tableau des scores inchangé -->
            </div>
        </main>

        <footer>
            <span data-translate="footer">© 2025 Simon Game - Test your memory skills</span>
        </footer>

        <div class="language-selector">
            <select id="languageSelect" onchange="changeLanguage(this.value)">
                <option value="fr">🇫🇷 Français</option>
                <option value="en" selected>🇬🇧 English</option>
                <option value="de">🇩🇪 Deutsch</option>
            </select>
        </div>
    </div>

    <script>
        const translations = {
            en: {
                title: "Simon",
                choose_level: "Choose Level",
                select_difficulty: "Select difficulty",
                easy: "Easy - Normal speed",
                medium: "Medium - Fast speed",
                hard: "Hard - Very fast speed",
                start_game: "Start Game",
                high_scores: "High Scores",
                position: "Position",
                player: "Player",
                score: "Score",
                difficulty: "Difficulty",
                hard_badge: "Hard",
                medium_badge: "Medium",
                easy_badge: "Easy",
                footer: "© 2025 Simon Game - Test your memory skills"
            },
            fr: {
                title: "Simon",
                choose_level: "Choisir le niveau",
                select_difficulty: "Sélectionner la difficulté",
                easy: "Facile - Vitesse normale",
                medium: "Moyen - Vitesse rapide",
                hard: "Difficile - Vitesse très rapide",
                start_game: "Commencer le jeu",
                high_scores: "Meilleurs scores",
                position: "Position",
                player: "Joueur",
                score: "Score",
                difficulty: "Difficulté",
                hard_badge: "Difficile",
                medium_badge: "Moyen",
                easy_badge: "Facile",
                footer: "© 2025 Jeu Simon - Testez votre mémoire"
            },
            de: {
                title: "Simon",
                choose_level: "Level wählen",
                select_difficulty: "Schwierigkeit wählen",
                easy: "Einfach - Normale Geschwindigkeit",
                medium: "Mittel - Schnelle Geschwindigkeit",
                hard: "Schwer - Sehr schnelle Geschwindigkeit",
                start_game: "Spiel starten",
                high_scores: "Bestenliste",
                position: "Position",
                player: "Spieler",
                score: "Punktzahl",
                difficulty: "Schwierigkeit",
                hard_badge: "Schwer",
                medium_badge: "Mittel",
                easy_badge: "Einfach",
                footer: "© 2025 Simon Spiel - Testen Sie Ihr Gedächtnis"
            }
        };

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

        document.addEventListener('DOMContentLoaded', function() {
            const userLang = navigator.language || navigator.userLanguage;
            const defaultLang = userLang.startsWith('fr') ? 'fr' : userLang.startsWith('de') ? 'de' : 'en';
            document.getElementById('languageSelect').value = defaultLang;
            changeLanguage(defaultLang);
        });
    </script>
</body>
</html>
