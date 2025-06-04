// Translation system
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
        footer: "© 2025 Simon Game - Test your memory skills",
        start: "Start",
        back_to_menu: "Back to Menu",
        new_game: "New Game",
        current_round: "Round:",
        game_over: "Game Over!",
        your_score: "Your Score:",
        enter_name: "Enter your name:",
        play_again: "Play Again"
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
        footer: "© 2025 Jeu Simon - Testez vos capacités de mémorisation",
        start: "Démarrer",
        back_to_menu: "Retour au menu",
        new_game: "Nouveau jeu",
        current_round: "Manche:",
        game_over: "Jeu terminé!",
        your_score: "Votre score:",
        enter_name: "Entrez votre nom:",
        play_again: "Rejouer"
    },
    de: {
        title: "Simon",
        choose_level: "Level wählen",
        select_difficulty: "Schwierigkeit auswählen",
        easy: "Einfach - Normale Geschwindigkeit",
        medium: "Mittel - Schnelle Geschwindigkeit",
        hard: "Schwer - Sehr schnelle Geschwindigkeit",
        start_game: "Spiel starten",
        high_scores: "Bestenliste",
        position: "Position",
        player: "Spieler",
        score: "Punkte",
        difficulty: "Schwierigkeit",
        hard_badge: "Schwer",
        medium_badge: "Mittel",
        easy_badge: "Einfach",
        footer: "© 2025 Simon Spiel - Teste dein Gedächtnis",
        start: "Start",
        back_to_menu: "Zurück zum Menü",
        new_game: "Neues Spiel",
        current_round: "Runde:",
        game_over: "Spiel vorbei!",
        your_score: "Dein Ergebnis:",
        enter_name: "Namen eingeben:",
        play_again: "Nochmal spielen"
    }
};

let currentLanguage = 'en';

// Simon Game Logic
class SimonGame {
    constructor() {
        this.sequence = [];
        this.playerSequence = [];
        this.score = 0;
        this.round = 1;
        this.difficulty = 'easy';
        this.isPlaying = false;
        this.isPlayerTurn = false;
        this.audioContext = null;
        
        this.speeds = {
            easy: 800,
            medium: 500,
            hard: 300
        };
        
        this.colors = ['green', 'red', 'yellow', 'blue'];
        this.frequencies = [261.63, 329.63, 392.00, 523.25]; // C4, E4, G4, C5
        
        this.initializeGame();
    }
    
    initializeGame() {
        this.initializeAudio();
        this.bindEvents();
        this.loadHighScores();
    }
    
    initializeAudio() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        } catch (error) {
            console.warn('Web Audio API not supported');
        }
    }
    
    bindEvents() {
        // Difficulty form submission
        document.getElementById('difficulty-form').addEventListener('submit', (e) => {
            e.preventDefault();
            const difficulty = document.getElementById('difficulty').value;
            if (difficulty) {
                this.startGame(difficulty);
            }
        });
        
        // Simon button clicks
        document.querySelectorAll('.simon-button').forEach((button, index) => {
            button.addEventListener('click', () => {
                if (this.isPlayerTurn) {
                    this.handlePlayerInput(index);
                }
            });
        });
        
        // Game control buttons
        document.getElementById('start-button').addEventListener('click', () => {
            this.nextRound();
        });
        
        document.getElementById('back-button').addEventListener('click', () => {
            this.backToMenu();
        });
        
        document.getElementById('new-game-button').addEventListener('click', () => {
            this.resetGame();
        });
    }
    
    startGame(difficulty) {
        this.difficulty = difficulty;
        this.resetGame();
        this.showGameView();
        this.updateDifficultyDisplay();
    }
    
    resetGame() {
        this.sequence = [];
        this.playerSequence = [];
        this.score = 0;
        this.round = 1;
        this.isPlaying = false;
        this.isPlayerTurn = false;
        this.updateDisplay();
    }
    
    showGameView() {
        document.getElementById('home-view').style.display = 'none';
        document.getElementById('game-view').style.display = 'flex';
    }
    
    showHomeView() {
        document.getElementById('home-view').style.display = 'flex';
        document.getElementById('game-view').style.display = 'none';
    }
    
    backToMenu() {
        this.showHomeView();
        this.loadHighScores();
    }
    
    updateDifficultyDisplay() {
        const difficultyElement = document.getElementById('current-difficulty');
        const difficultyMap = {
            easy: 'easy-badge',
            medium: 'medium-badge',
            hard: 'hard-badge'
        };
        
        difficultyElement.className = `difficulty-display difficulty-badge ${difficultyMap[this.difficulty]}`;
        difficultyElement.textContent = translations[currentLanguage][`${this.difficulty}_badge`];
    }
    
    updateDisplay() {
        document.getElementById('score-display').textContent = this.score;
        document.getElementById('round-number').textContent = this.round;
        
        const startButton = document.getElementById('start-button');
        if (this.isPlaying) {
            startButton.style.display = 'none';
        } else {
            startButton.style.display = 'block';
            startButton.textContent = this.score > 0 ? translations[currentLanguage].play_again : translations[currentLanguage].start;
        }
    }
    
    nextRound() {
        if (this.audioContext && this.audioContext.state === 'suspended') {
            this.audioContext.resume();
        }
        
        this.isPlaying = true;
        this.isPlayerTurn = false;
        this.playerSequence = [];
        
        // Add new color to sequence
        const newColor = Math.floor(Math.random() * 4);
        this.sequence.push(newColor);
        
        this.updateDisplay();
        this.playSequence();
    }
    
    playSequence() {
        let index = 0;
        const speed = this.speeds[this.difficulty];
        
        const playNext = () => {
            if (index < this.sequence.length) {
                this.activateButton(this.sequence[index]);
                this.playSound(this.sequence[index]);
                
                setTimeout(() => {
                    this.deactivateButton(this.sequence[index]);
                    index++;
                    setTimeout(playNext, speed * 0.3);
                }, speed * 0.7);
            } else {
                // Sequence finished, player's turn
                this.isPlayerTurn = true;
            }
        };
        
        setTimeout(playNext, 500);
    }
    
    handlePlayerInput(buttonIndex) {
        this.activateButton(buttonIndex);
        this.playSound(buttonIndex);
        
        setTimeout(() => {
            this.deactivateButton(buttonIndex);
        }, 200);
        
        this.playerSequence.push(buttonIndex);
        
        // Check if player input is correct
        const currentIndex = this.playerSequence.length - 1;
        if (this.playerSequence[currentIndex] !== this.sequence[currentIndex]) {
            this.gameOver();
            return;
        }
        
        // Check if player completed the sequence
        if (this.playerSequence.length === this.sequence.length) {
            this.score++;
            this.round++;
            this.isPlayerTurn = false;
            
            setTimeout(() => {
                this.nextRound();
            }, 1000);
        }
    }
    
    activateButton(index) {
        const button = document.querySelectorAll('.simon-button')[index];
        button.classList.add('active');
    }
    
    deactivateButton(index) {
        const button = document.querySelectorAll('.simon-button')[index];
        button.classList.remove('active');
    }
    
    playSound(index) {
        if (!this.audioContext) return;
        
        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);
        
        oscillator.frequency.setValueAtTime(this.frequencies[index], this.audioContext.currentTime);
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, this.audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.5);
        
        oscillator.start(this.audioContext.currentTime);
        oscillator.stop(this.audioContext.currentTime + 0.5);
    }
    
    gameOver() {
        this.isPlaying = false;
        this.isPlayerTurn = false;
        
        // Play error sound
        if (this.audioContext) {
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            oscillator.frequency.setValueAtTime(150, this.audioContext.currentTime);
            oscillator.type = 'square';
            
            gainNode.gain.setValueAtTime(0.3, this.audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 1);
            
            oscillator.start(this.audioContext.currentTime);
            oscillator.stop(this.audioContext.currentTime + 1);
        }
        
        setTimeout(() => {
            this.saveHighScore();
            this.updateDisplay();
        }, 1000);
    }
    
    saveHighScore() {
        if (this.score === 0) return;
        
        const playerName = prompt(
            `${translations[currentLanguage].game_over}\n${translations[currentLanguage].your_score} ${this.score}\n${translations[currentLanguage].enter_name}`
        ) || 'Anonymous';
        
        const highScores = this.getHighScores();
        highScores.push({
            name: playerName,
            score: this.score,
            difficulty: this.difficulty,
            date: new Date().toISOString()
        });
        
        // Sort by score descending
        highScores.sort((a, b) => b.score - a.score);
        
        // Keep only top 10
        const topScores = highScores.slice(0, 10);
        
        localStorage.setItem('simonHighScores', JSON.stringify(topScores));
    }
    
    getHighScores() {
        const scores = localStorage.getItem('simonHighScores');
        return scores ? JSON.parse(scores) : [];
    }
    
    loadHighScores() {
        const tbody = document.getElementById('scores-tbody');
        const highScores = this.getHighScores();
        
        if (highScores.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" style="text-align: center; opacity: 0.7;">
                        No scores yet - be the first to play!
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = '';
        
        highScores.forEach((score, index) => {
            const row = document.createElement('tr');
            const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `${index + 1}.`;
            const badgeClass = `${score.difficulty}-badge`;
            
            row.innerHTML = `
                <td>${medal}</td>
                <td>${score.name}</td>
                <td>${score.score}</td>
                <td><span class="difficulty-badge ${badgeClass}" data-translate="${score.difficulty}_badge">${translations[currentLanguage][`${score.difficulty}_badge`]}</span></td>
            `;
            
            tbody.appendChild(row);
        });
    }
}

// Language functionality
function changeLanguage(lang) {
    currentLanguage = lang;
    localStorage.setItem('simonLanguage', lang);
    updateTranslations();
    
    // Update high scores table with new language
    if (window.simonGame) {
        window.simonGame.loadHighScores();
        window.simonGame.updateDifficultyDisplay();
    }
}

function updateTranslations() {
    const elements = document.querySelectorAll('[data-translate]');
    elements.forEach(element => {
        const key = element.getAttribute('data-translate');
        if (translations[currentLanguage] && translations[currentLanguage][key]) {
            if (key === 'current_round') {
                element.innerHTML = `${translations[currentLanguage][key]} <span id="round-number">${document.getElementById('round-number')?.textContent || '1'}</span>`;
            } else {
                element.textContent = translations[currentLanguage][key];
            }
        }
    });
}

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    // Load saved language preference
    const savedLanguage = localStorage.getItem('simonLanguage');
    if (savedLanguage && translations[savedLanguage]) {
        currentLanguage = savedLanguage;
        document.getElementById('languageSelect').value = savedLanguage;
    }
    
    updateTranslations();
    
    // Initialize Simon game
    window.simonGame = new SimonGame();
});

// Handle audio context for mobile devices
document.addEventListener('touchstart', () => {
    if (window.simonGame && window.simonGame.audioContext && window.simonGame.audioContext.state === 'suspended') {
        window.simonGame.audioContext.resume();
    }
}, { once: true });

document.addEventListener('click', () => {
    if (window.simonGame && window.simonGame.audioContext && window.simonGame.audioContext.state === 'suspended') {
        window.simonGame.audioContext.resume();
    }
}, { once: true });
