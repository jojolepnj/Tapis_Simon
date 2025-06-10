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
    <link rel="stylesheet" href="style.css">
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
