
using Toybox.Application;
using Toybox.WatchUi;

class helloApp extends Application.AppBase {

    function initialize() {
        AppBase.initialize();
    }

    // Retourne la vue initiale
    function getInitialView() {
        return [ new helloView() ];  // Plus besoin du delegate pour un simple affichage
    }
}

function getApp() {
    return Application.getApp() as helloApp;
}