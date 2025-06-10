import Toybox.Lang;
import Toybox.WatchUi;

class helloDelegate extends WatchUi.BehaviorDelegate {

    function initialize() {
        BehaviorDelegate.initialize();
    }

    function onMenu() as Boolean {
        WatchUi.pushView(new Rez.Menus.MainMenu(), new helloMenuDelegate(), WatchUi.SLIDE_UP);
        return true;
    }

}