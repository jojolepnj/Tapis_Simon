<?php
/**
 * @file simon.php
 * @brief Page principale du jeu Simon - Interface de sélection de difficulté
 *
 * Cette page web constitue l'interface principale du jeu Simon.
 * Elle permet aux utilisateurs de :
 * - Sélectionner le niveau de difficulté du jeu
 * - Changer la langue de l'interface
 * - Lancer une nouvelle partie
 *
 * @author Treliann
 * 
 * @requires PHP 7.4+
 * @requires phpMQTT.php
 */

// Configuration de l'encodage UTF-8
header('Content-Type: text/html; charset=UTF-8');
mb_internal_encoding('UTF-8');
mb_http_output('UTF-8');
?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Simon Game</title>
    <style>
        /**
         * @section Variables CSS Globales
         * @description Définition des couleurs et dimensions principales du jeu
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
         * @description Styles fondamentaux pour le body et html
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

        html {
            height: -webkit-fill-available;
        }

        /**
         * @section Arrière-plan Décoratif
         * @description Cercle SVG en arrière-plan
         */
        body::before {
            content: '';
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: min(200vw, 200vh);
            height: min(200vw, 200vh);
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 1000 1000' xmlns='http://www.w3.org/2000/svg'%3E%3Cg transform='translate(500, 500)'%3E%3Ccircle cx='0' cy='0' r='480' fill='none' stroke='%23ffffff0d' stroke-width='2'/%3E%3C/g%3E%3C/svg%3E");
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center;
            opacity: 0.3;
            z-index: 0;
            pointer-events: none;
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
         * @description Styles pour l'en-tête et le titre
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
         * @section Grille de Jeu
         * @description Layout principal des panneaux de jeu
         */
        .game-panel {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
            gap: clamp(1rem, 3vw, 2rem);
            flex: 1;
        }

        /**
         * @section Panneaux
         * @description Styles communs pour les panneaux de jeu
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

        .highscores-panel {
            border: 2px solid var(--simon-red);
            box-shadow: 0 0 30px rgba(255, 51, 51, 0.2);
        }

        /**
         * @section Formulaire de Difficulté
         * @description Styles pour le formulaire de sélection de difficulté
         */
        .difficulty-form {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .form-select {
            width: 100%;
            padding: clamp(0.8rem, 2vw, 1.2rem);
            border-radius: var(--radius);
            background: rgba(255, 255, 255, 0.1);
            border: 2px solid var(--simon-green);
            color: var(--light);
            font-size: clamp(0.9rem, 2vw, 1.1rem);
            cursor: pointer;
        }

        .form-select option {
            background: var(--dark);
            color: var(--light);
            padding: 0.5rem;
        }

        /**
         * @section Boutons
         * @description Styles pour les boutons principaux
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
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }

        /**
         * @section Tableau des Scores
         * @description Styles pour le tableau des meilleurs scores
         */
        .score-table {
            width: 100%;
            border-collapse: collapse;
            font-size: clamp(0.8rem, 2vw, 1rem);
        }

        .score-table th,
        .score-table td {
            padding: clamp(0.5rem, 1.5vw, 1rem);
            text-align: left;
        }

        .score-table th {
            background: linear-gradient(45deg, var(--simon-red), var(--simon-yellow));
            white-space: nowrap;
        }

        .score-table td {
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        /**
         * @section Badges de Difficulté
         * @description Styles pour les indicateurs de difficulté
         */
        .difficulty-badge {
            padding: 0.3em 0.6em;
            border-radius: 1em;
            font-size: 0.85em;
            font-weight: bold;
            display: inline-block;
            text-transform: uppercase;
        }

        .easy-badge { background: var(--simon-green); }
        .medium-badge { background: var(--simon-yellow); color: #000; }
        .hard-badge { background: var(--simon-red); }

        /**
         * @section Sélecteur de Langue
         * @description Styles pour le sélecteur de langue
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
         * @section Pied de Page
         * @description Styles pour le pied de page
         */
        footer {
            text-align: center;
            font-size: clamp(0.8rem, 2vw, 1rem);
            opacity: 0.7;
            padding: 1rem 0;
        }

        /**
         * @section Media Queries
         * @description Adaptations responsives
         */
        @media (max-width: 480px) {
            .score-table {
                display: block;
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
            }

            .score-table thead {
                position: sticky;
                top: 0;
                z-index: 1;
            }

            .panel {
                max-height: 80vh;
                overflow-y: auto;
            }

            .container {
                padding: 0.5rem;
            }
        }

        @media (hover: hover) {
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4);
                background: linear-gradient(45deg, var(--simon-blue), var(--simon-green));
            }

            .form-select:hover {
                border-color: var(--simon-yellow);
                box-shadow: 0 0 15px rgba(255, 204, 0, 0.3);
            }

            .language-selector select:hover {
                border-color: var(--simon-blue);
                box-shadow: 0 0 15px rgba(51, 153, 255, 0.3);
            }
        }

        @media (orientation: landscape) and (max-height: 500px) {
            .container {
                min-height: auto;
            }

            .game-panel {
                grid-template-columns: repeat(2, 1fr);
            }
        }
    </style>
</head>
<body>
    <!-- Structure principale -->
    <div class="container">
        <!-- En-tête avec titre -->
        <header class="game-header">
            <h1 class="game-title" data-translate="title">Simon Game</h1>
        </header>

        <!-- Zone de jeu principale -->
        <main class="game-panel">
            <!-- Panneau de contrôle -->
            <div class="control-panel panel">
                <form id="difficulty-form" class="difficulty-form" action="retour.php" method="post">
                    <select name="difficulty" class="form-select">
                        <option value="easy" data-translate="easy">Facile</option>
                        <option value="medium" data-translate="medium">Moyen</option>
                        <option value="hard" data-translate="hard">Difficile</option>
                    </select>
                    <input type="hidden" name="selected_language" id="selected_language" value="fr">
                    <button type="submit" class="btn-primary" data-translate="start_game">Demarrer le jeu</button>
                </form>
            </div>

            <!-- Panneau des scores -->
            <div class="highscores-panel panel">
                <table class="score-table">
                    <thead>
                        <tr>
                            <th data-translate="player">Joueur</th>
                            <th data-translate="score">Score</th>
                            <th data-translate="difficulty">Difficulte</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>PlayerOne</td>
                            <td>15</td>
                            <td><span class="difficulty-badge hard-badge" data-translate="hard">Difficile</span></td>
                        </tr>
                        <tr>
                            <td>PlayerTwo</td>
                            <td>12</td>
                            <td><span class="difficulty-badge medium-badge" data-translate="medium">Moyen</span></td>
                        </tr>
                        <tr>
                            <td>PlayerThree</td>
                            <td>8</td>
                            <td><span class="difficulty-badge easy-badge" data-translate="easy">Facile</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </main>

        <!-- Pied de page -->
        <footer>
            <span data-translate="footer">2025 Simon Game - Testez votre memoire</span>
        </footer>

        <!-- Sélecteur de langue -->
        <div class="language-selector">
            <select id="languageSelect" onchange="changeLanguage(this.value)">
                <option value="fr">[FR] Francais</option>
                <option value="en">[EN] English</option>
                <option value="de">[DE] Deutsch</option>
            </select>
        </div>
    </div>

    <!-- Scripts -->
    <script>
    /**
     * @namespace SimonGame
     * @description Espace de noms pour les fonctionnalités du jeu Simon
     */

    /**
     * @typedef {Object} Translation
     * @property {string} title - Titre du jeu
     * @property {string} easy - Niveau facile
     * @property {string} medium - Niveau moyen
     * @property {string} hard - Niveau difficile
     * @property {string} start_game - Texte du bouton démarrer
     * @property {string} player - En-tête colonne joueur
     * @property {string} score - En-tête colonne score
     * @property {string} difficulty - En-tête colonne difficulté
     * @property {string} footer - Texte du pied de page
     */

    /**
     * @constant {Object.<string, Translation>}
     * @description Objet contenant toutes les traductions disponibles
     * @memberof SimonGame
     */
    const translations = {
        en: {
            title: "Simon Game",
            easy: "Easy",
            medium: "Medium",
            hard: "Hard",
            start_game: "Start Game",
            player: "Player",
            score: "Score",
            difficulty: "Difficulty",
            footer: "2025 Simon Game - Test your memory skills"
        },
        fr: {
            title: "Simon Game",
            easy: "Facile",
            medium: "Moyen",
            hard: "Difficile",
            start_game: "Demarrer le jeu",
            player: "Joueur",
            score: "Score",
            difficulty: "Difficulte",
            footer: "2025 Simon Game - Testez votre memoire"
        },
        de: {
            title: "Simon Spiel",
            easy: "Einfach",
            medium: "Mittel",
            hard: "Schwer",
            start_game: "Spiel starten",
            player: "Spieler",
            score: "Punktzahl",
            difficulty: "Schwierigkeit",
            footer: "2025 Simon Spiel - Testen Sie Ihr Gedachtnis"
        }
    };

    /**
     * @function changeLanguage
     * @description Change la langue de l'interface utilisateur
     * @param {string} lang - Code de la langue à appliquer (fr|en|de)
     * @memberof SimonGame
     * @example
     * changeLanguage('fr'); // Change la langue en français
     * @returns {void}
     */
    function changeLanguage(lang) {
        document.documentElement.lang = lang;
        localStorage.setItem('selectedLanguage', lang);
        document.getElementById('selected_language').value = lang;

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

        document.getElementById('languageSelect').value = lang;
    }

    /**
     * @function initializeLanguage
     * @description Initialise la langue de l'interface au chargement de la page
     * @memberof SimonGame
     * @listens DOMContentLoaded
     * @returns {void}
     */
    document.addEventListener('DOMContentLoaded', function initializeLanguage() {
        const savedLang = localStorage.getItem('selectedLanguage');
        const userLang = navigator.language || navigator.userLanguage;
        const initialLang = savedLang || (userLang.startsWith('fr') ? 'fr' : 
                                        userLang.startsWith('de') ? 'de' : 'en');
        
        changeLanguage(initialLang);
    });
    </script>
</body>
</html>
