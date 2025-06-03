<?php
/**
 * @file retour.php
 * @brief Page de transition et communication MQTT pour le jeu Simon
 * @details
 * Cette page gère :
 * - La réception des paramètres de jeu (difficulté, langue)
 * - La communication avec le broker MQTT
 * - L'envoi des commandes de démarrage au jeu
 * - L'affichage d'une confirmation de lancement
 * 
 * @author Treliann
 *
 * @requires PHP 7.4+
 * @requires phpMQTT.php
 */

/**
 * @brief Configure les paramètres d'erreur et l'encodage
 */
error_reporting(E_ALL);
ini_set('display_errors', 1);
header('Content-Type: text/html; charset=UTF-8');
mb_internal_encoding('UTF-8');
mb_http_output('UTF-8');

/**
 * @function debug_log
 * @brief Fonction de journalisation pour le débogage
 * @param string $message Message à enregistrer
 * @return void
 */
function debug_log($message) {
    error_log($message);
    echo "<!-- Debug: " . htmlspecialchars($message) . " -->\n";
}

// Inclusion de la bibliothèque MQTT
require("phpMQTT.php");

// Configuration de la connexion MQTT
$server = "10.0.200.7";     // Adresse du broker MQTT
$port = 1883;               // Port standard MQTT
$client_id = "phpMQTT-simon-" . uniqid();

// Récupération de la langue sélectionnée
$selected_language = isset($_POST['selected_language']) ? $_POST['selected_language'] : 'fr';

/**
 * @section Traitement MQTT
 * @brief Gestion de la communication MQTT pour le démarrage du jeu
 */
if (isset($_POST['difficulty'])) {
    $difficulty = $_POST['difficulty'];
    
    // Correspondance des niveaux de difficulté
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
            
            // Envoi du niveau de difficulté
            $difficulty_message = json_encode(['dif' => $difficulty_map[$difficulty]]);
            if ($mqtt->publish("site/difficulte", $difficulty_message, 0)) {
                debug_log("Message de difficulté envoyé: $difficulty_message");
            }
            
            // Délai court pour assurer la séquence
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
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title data-translate="title">Page de Jeu</title>
    <style>
        /**
         * @section Variables CSS Globales
         * @description Définition des couleurs et dimensions principales
         */
        :root {
            --simon-green: #00cc66;    /* Couleur verte pour le bouton Simon */
            --simon-red: #ff3333;      /* Couleur rouge pour le bouton Simon */
            --simon-yellow: #ffcc00;   /* Couleur jaune pour le bouton Simon */
            --simon-blue: #3399ff;     /* Couleur bleue pour le bouton Simon */
            --dark: #1a1a2e;           /* Couleur de fond sombre */
            --light: #f6f6f6;          /* Couleur claire pour le texte */
            --spacing-md: clamp(1rem, 2vw, 2rem); /* Espacement adaptatif */
            --radius: 15px;            /* Rayon des coins arrondis */
        }

        /**
         * @section Reset CSS
         * @description Réinitialisation des styles par défaut
         */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }

        /**
         * @section Styles de Base
         * @description Styles fondamentaux pour le body
         */
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            min-height: 100vh;
            min-height: -webkit-fill-available;
            background-color: var(--dark);
            color: var(--light);
            overflow-x: hidden;
            position: relative;
        }

        /**
         * @section Container Principal
         * @description Conteneur principal de la page
         */
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

        /**
         * @section En-tête du Jeu
         * @description Styles pour l'en-tête
         */
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

        /**
         * @section Bouton Principal
         * @description Style du bouton de retour
         */
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

        /**
         * @section Panneau de Contrôle
         * @description Style du panneau principal
         */
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

        /**
         * @section Sélecteur de Langue
         * @description Style du sélecteur de langue
         */
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

        /**
         * @section Messages de Débogage
         * @description Style pour les messages de débogage
         */
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
            <span data-translate="footer">2025 Simon Game - Testez votre memoire</span>
        </footer>

        <div class="language-selector">
            <select id="languageSelect" onchange="changeLanguage(this.value)">
                <option value="fr">[FR] Francais</option>
                <option value="en">[EN] English</option>
                <option value="de">[DE] Deutsch</option>
            </select>
        </div>
    </div>

    <script>
    /**
     * @namespace RetourPage
     * @description Gestion des traductions et de la langue pour la page de retour
     */

    /**
     * @constant {Object} translations
     * @description Objet contenant toutes les traductions
     * @memberof RetourPage
     */
    const translations = {
        en: {
            title: "Game Page",
            game_launched: "The game has been launched",
            return_to_game: "Return to game",
            footer: "2025 Simon Game - Test your memory skills"
        },
        fr: {
            title: "Page de Jeu",
            game_launched: "Le jeu a été lancé",
            return_to_game: "Retour au jeu",
            footer: "2025 Simon Game - Testez votre memoire"
        },
        de: {
            title: "Spielseite",
            game_launched: "Das Spiel wurde gestartet",
            return_to_game: "Zurück zum Spiel",
            footer: "2025 Simon Spiel - Testen Sie Ihr Gedachtnis"
        }
    };

    /**
     * @function changeLanguage
     * @description Change la langue de l'interface
     * @param {string} lang - Code de la langue à appliquer
     * @memberof RetourPage
     */
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

    /**
     * @function initializeLanguage
     * @description Initialise la langue au chargement de la page
     * @memberof RetourPage
     * @listens DOMContentLoaded
     */
    document.addEventListener('DOMContentLoaded', function() {
        // Utilise la langue transmise par le formulaire
        const selectedLang = "<?php echo $selected_language; ?>";
        document.getElementById('languageSelect').value = selectedLang;
        changeLanguage(selectedLang);
    });
    </script>

    <?php if (isset($_GET['debug'])): ?>
    <!-- Section de débogage -->
    <div class="debug-messages">
        <?php
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
