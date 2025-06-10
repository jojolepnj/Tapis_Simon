// Importation des modules nécessaires
using Toybox.WatchUi;      // Pour l'interface utilisateur
using Toybox.Graphics;     // Pour le dessin à l'écran
using Toybox.System;       // Pour les fonctions système
using Toybox.Sensor;       // Pour accéder aux capteurs
using Toybox.Timer;        // Pour les minuteries
using Toybox.Lang;         // Pour les fonctionnalités de langage de base

// Classe principale de la vue qui hérite de WatchUi.View
class BioMetricsView extends WatchUi.View {
    // Variables membres de la classe
    protected var heartRate = "--";      // Stocke la fréquence cardiaque (protected pour l'accès indirect)
    private var timer;                   // Timer pour les mises à jour régulières
    private var hrReadings = new [5];    // Tableau pour stocker les 5 dernières mesures
    private var readingIndex = 0;        // Index courant dans le tableau des mesures
    private const UPDATE_INTERVAL = 1000; // Intervalle de mise à jour en millisecondes
    private var errorMessage = null;      // Message d'erreur à afficher si nécessaire

    // Fonction d'initialisation appelée à la création de la vue
    function initialize() {
        View.initialize();               // Appel du constructeur parent
        timer = new Timer.Timer();       // Création du timer

        // Initialisation du tableau des mesures avec des valeurs null
        for (var i = 0; i < hrReadings.size(); i++) {
            hrReadings[i] = null;
        }

        // Configuration des capteurs et démarrage des mesures
        try {
            // Active le capteur de fréquence cardiaque
            Sensor.setEnabledSensors([Sensor.SENSOR_HEARTRATE]);
            // Configure le callback pour les événements du capteur
            Sensor.enableSensorEvents(method(:onSensor));
            // Démarre le timer pour les mises à jour régulières
            timer.start(method(:requestSensorData), UPDATE_INTERVAL, true);
        } catch(ex) {
            // En cas d'erreur, stocke et affiche le message
            errorMessage = ex.getErrorMessage();
            System.println("Erreur capteur : " + errorMessage);
        }
    }

    // Calcule la moyenne des mesures non-nulles
    function calculateAverage(readings) {
        var sum = 0;
        var count = 0;
        // Parcourt toutes les mesures
        for (var i = 0; i < readings.size(); i++) {
            if (readings[i] != null) {
                sum += readings[i];
                count++;
            }
        }
        // Retourne la moyenne ou null si aucune mesure valide
        return (count > 0) ? (sum / count).toNumber() : null;
    }

    // Fonction de dessin de l'interface
    function onUpdate(dc) {
        // Configure le fond en noir
        dc.setColor(Graphics.COLOR_BLACK, Graphics.COLOR_BLACK);
        dc.clear();

        // Configure la couleur du texte en blanc
        dc.setColor(Graphics.COLOR_WHITE, Graphics.COLOR_TRANSPARENT);

        // Affiche le titre de l'application
        dc.drawText(
            dc.getWidth() / 2,
            30,
            Graphics.FONT_MEDIUM,
            WatchUi.loadResource(Rez.Strings.AppName),
            Graphics.TEXT_JUSTIFY_CENTER
        );

        // Affiche le message d'erreur si présent
        if (errorMessage != null) {
            dc.drawText(
                dc.getWidth() / 2,
                dc.getHeight() / 2,
                Graphics.FONT_SMALL,
                errorMessage,
                Graphics.TEXT_JUSTIFY_CENTER
            );
            return;
        }

        // Affiche le libellé "Heart Rate" et la valeur
        dc.drawText(
            dc.getWidth() / 2,
            dc.getHeight() / 2 - 30,
            Graphics.FONT_SMALL,
            WatchUi.loadResource(Rez.Strings.HeartRate),
            Graphics.TEXT_JUSTIFY_CENTER
        );
        dc.drawText(
            dc.getWidth() / 2,
            dc.getHeight() / 2,
            Graphics.FONT_LARGE,
            self.heartRate + " bpm",
            Graphics.TEXT_JUSTIFY_CENTER
        );
    }

    // Fonction appelée régulièrement par le timer pour récupérer les données
    function requestSensorData() {
        try {
            var sensorInfo = Sensor.getInfo();
            if (sensorInfo has :heartRate && sensorInfo.heartRate != null) {
                System.println("Lecture HR : " + sensorInfo.heartRate);
                // Stocke la nouvelle mesure et met à jour la moyenne
                hrReadings[readingIndex] = sensorInfo.heartRate;
                var avgHR = calculateAverage(hrReadings);
                if (avgHR != null) {
                    self.heartRate = avgHR.toString();
                    System.println("Moyenne HR : " + self.heartRate);
                }
            }
            // Avance l'index de manière circulaire
            readingIndex = (readingIndex + 1) % hrReadings.size();
            WatchUi.requestUpdate();
        } catch (ex) {
            System.println("Erreur lecture HR : " + ex.getErrorMessage());
        }
    }

    // Callback appelé lors d'un événement du capteur
    function onSensor(sensorInfo as Sensor.Info) as Void {
        if (sensorInfo != null && sensorInfo.heartRate != null) {
            try {
                System.println("Event HR : " + sensorInfo.heartRate);
                // Même traitement que requestSensorData
                hrReadings[readingIndex] = sensorInfo.heartRate;
                var avgHR = calculateAverage(hrReadings);
                if (avgHR != null) {
                    self.heartRate = avgHR.toString();
                    System.println("Moyenne HR : " + self.heartRate);
                }
                readingIndex = (readingIndex + 1) % hrReadings.size();
                WatchUi.requestUpdate();
            } catch (ex) {
                System.println("Erreur traitement HR : " + ex.getErrorMessage());
            }
        }
    }

    // Appelé quand la vue devient visible
    function onShow() {
        requestSensorData();
    }

    // Appelé quand la vue est masquée
    function onHide() {
        timer.stop();                    // Arrête le timer
        Sensor.setEnabledSensors([]);    // Désactive les capteurs
    }
}