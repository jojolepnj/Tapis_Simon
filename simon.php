<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Simon Game</title>
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

        html {
            height: -webkit-fill-available;
        }

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

        .game-panel {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
            gap: clamp(1rem, 3vw, 2rem);
            flex: 1;
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

        .highscores-panel {
            border: 2px solid var(--simon-red);
            box-shadow: 0 0 30px rgba(255, 51, 51, 0.2);
        }

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

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4);
            background: linear-gradient(45deg, var(--simon-blue), var(--simon-green));
        }

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

        footer {
            text-align: center;
            font-size: clamp(0.8rem, 2vw, 1rem);
            opacity: 0.7;
            padding: 1rem 0;
        }

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
    <div class="container">
        <header class="game-header">
            <h1 class="game-title" data-translate="title">Simon Game</h1>
        </header>

        <main class="game-panel">
            <div class="control-panel panel">
                <form id="difficulty-form" class="difficulty-form" action="retour.php" method="post">
                    <select name="difficulty" class="form-select">
                        <option value="easy" data-translate="easy">Facile</option>
                        <option value="medium" data-translate="medium">Moyen</option>
                        <option value="hard" data-translate="hard">Difficile</option>
                    </select>
                    <input type="hidden" name="selected_language" id="selected_language" value="fr">
                    <button type="submit" class="btn-primary" data-translate="start_game">Démarrer le jeu</button>
                </form>
            </div>

            <div class="highscores-panel panel">
                <table class="score-table">
                    <thead>
                        <tr>
                            <th data-translate="player">Joueur</th>
                            <th data-translate="score">Score</th>
                            <th data-translate="difficulty">Difficulté</th>
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
                title: "Simon Game",
                easy: "Easy",
                medium: "Medium",
                hard: "Hard",
                start_game: "Start Game",
                player: "Player",
                score: "Score",
                difficulty: "Difficulty",
                footer: "© 2025 Simon Game - Test your memory skills"
            },
            fr: {
                title: "Simon Game",
                easy: "Facile",
                medium: "Moyen",
                hard: "Difficile",
                start_game: "Démarrer le jeu",
                player: "Joueur",
                score: "Score",
                difficulty: "Difficulté",
                footer: "© 2025 Simon Game - Testez votre mémoire"
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
                footer: "© 2025 Simon Spiel - Testen Sie Ihr Gedächtnis"
            }
        };

        function changeLanguage(lang) {
            document.documentElement.lang = lang;
            // Mettre à jour le champ caché
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
