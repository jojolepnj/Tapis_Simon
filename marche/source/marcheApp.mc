// Importation des modules nécessaires pour l'application
using Toybox.Application;  // Module principal pour l'application
using Toybox.WatchUi;     // Interface utilisateur de la montre
using Toybox.System;      // Fonctionnalités système
using Toybox.Sensor;      // Accès aux capteurs de la montre

// Classe principale de l'application qui hérite de AppBase
class BioMetricsApp extends Application.AppBase {
    // Variable pour stocker l'instance de la vue principale
    private var view;

    // Constructeur de la classe
    function initialize() {
        AppBase.initialize();  // Appel du constructeur parent
    }

    // Fonction appelée au démarrage de l'application
    function onStart(state) {
        // Création d'un nouveau delegate pour gérer les interactions utilisateur
        var delegate = new BioMetricsDelegate();
        // Affiche la vue principale avec son delegate et une transition immédiate
        WatchUi.pushView(new BioMetricsView(), delegate, WatchUi.SLIDE_IMMEDIATE);
        
        // Log de démarrage
        System.println("Application starting...");
        
        try {
            // Vérifie si la montre possède les capteurs nécessaires
            var info = Sensor.getInfo();
            // Vérifie spécifiquement la présence du capteur cardiaque
            if (!(info has :heartRate)) {
                System.println("Warning: Heart rate sensor not available");
            }
        } catch(ex) {
            // Gestion des erreurs lors de la vérification des capteurs
            System.println("Error checking sensors: " + ex.getErrorMessage());
        }
    }

    // Fonction appelée lors de l'arrêt de l'application
    function onStop(state) {
        System.println("Application stopping...");
        // Si la vue existe, nettoie les ressources
        if (view != null) {
            view.onHide(); // Arrête les capteurs et les timers
        }
    }

    // Retourne la vue initiale de l'application
    function getInitialView() {
        // Crée une nouvelle instance de la vue
        view = new BioMetricsView();
        // Retourne un tableau contenant la vue et son delegate
        return [view, new BioMetricsDelegate()];
    }
}

// Classe déléguée pour gérer les interactions utilisateur
class BioMetricsDelegate extends WatchUi.BehaviorDelegate {
    // Constructeur du delegate
    function initialize() {
        BehaviorDelegate.initialize();  // Appel du constructeur parent
    }

    // Gestion de l'événement du bouton retour
    function onBack() {
        // Ferme la vue actuelle avec une transition immédiate
        WatchUi.popView(WatchUi.SLIDE_IMMEDIATE);
        return true;  // Indique que l'événement a été traité
    }

    // Gestion de l'événement du bouton select/entrée
    function onSelect() {
        // Pour l'instant, ne fait rien mais peut être étendu pour ajouter des fonctionnalités
        return true;  // Indique que l'événement a été traité
    }
}