
using Toybox.Graphics;
using Toybox.WatchUi;

class helloView extends WatchUi.View {

    function initialize() {
        View.initialize();
    }

    // Fonction de mise à jour de l'affichage
    function onUpdate(dc) {
        // Efface l'écran avec un fond noir
        dc.setColor(Graphics.COLOR_BLACK, Graphics.COLOR_BLACK);
        dc.clear();
        
        // Configure la couleur du texte en blanc
        dc.setColor(Graphics.COLOR_WHITE, Graphics.COLOR_TRANSPARENT);
        
        // Affiche "Hello World" au centre de l'écran
        dc.drawText(
            dc.getWidth() / 2,    // Position X (centre)
            dc.getHeight() / 2,   // Position Y (centre)
            Graphics.FONT_LARGE,   // Police de caractères
            "Hello World",        // Texte à afficher
            Graphics.TEXT_JUSTIFY_CENTER   // Alignement centré
        );
    }
}