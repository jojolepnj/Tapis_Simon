<?php


require_once("config.php");

// lien vers la base de données 
$pdo = null;


/** 
 * Connexion à la base de données
 */
function bddConnect() {
    global $pdo;
    try {
      $pdo = new PDO("mysql:host=".SERVER.";dbname=".BDD.";charset=utf8",
                   USER, PWD,
                   array(PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION)); 
    } catch (Exception $e) {
        echo $e->getMessage();
        $pdo = null;
        die();
    }
}


 /*function chercheJoueur($tag){
	 global $pdo;
    
	if ($pdo==null) bddConnect();
	
	try{ 
	// recherche du tag dans la base de données
	$sql = "SELECT id, pseudo from Player p join tags t on p.fk_Badge=t.id where t.Tag = $tag";
		$stmt = $pdo->prepare($sql);
		$stmt->bindParam(':tag', $tag); 
		$stmt->execute(); 
		$cpt = $stmt->rowCount();
		if ($cpt) != 0){
			$infos = $stmt
			$pseudo = 
		
	
	}
	 catch (PDOException $e) { // En cas d'erreur, on annule la transaction $pdo->rollBack(); 
		  echo "Erreur : " . $e->getMessage(); 
        return false;
    } 
 }*/




function ajoutePassage($tag){
    global $pdo;
    
	if ($pdo==null)
	 bddConnect();
	// recherche du tag dans la base de données
	
	
    
    try {
		
		$sql = "INSERT INTO Passage_tag (tag) VALUES (:tag)";
		$stmt = $pdo->prepare($sql);
		$stmt->bindParam(':tag', $tag); 
		$stmt->execute(); 
    
      return 1;
    } 
    catch (PDOException $e) { // En cas d'erreur, on annule la transaction $pdo->rollBack(); 
		  echo "Erreur : " . $e->getMessage(); 
        return false;
    } 
}



if(isset($_POST['tag'])){
	 
	if (chercheJoueurs($_POST['tag']) )  ajoutePassage($_POST['tag']);
	//header("location:" . "index.php");
	}
	
?>




