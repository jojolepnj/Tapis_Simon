<?php
// Paramètres de connexion à la base de données
$host = 'localhost';
$dbname = 'projet_simon';
$user = 'root';
$password = 'motdepasse'; // à adapter

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8", $user, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (PDOException $e) {
    die("Erreur de connexion à la base de données : " . $e->getMessage());
}

// Vérification des données reçues
if (isset($_POST['tag_uid'])) {
    $tag_uid = htmlspecialchars(trim($_POST['tag_uid']));

    // Requête d'insertion
    $sql = "INSERT INTO joueurs (tag_uid) VALUES (:tag_uid)";
    $stmt = $pdo->prepare($sql);
    
    try {
        $stmt->execute(['tag_uid' => $tag_uid]);
        echo "Tag NFC inséré avec succès.";
    } catch (PDOException $e) {
        echo "Erreur lors de l'insertion : " . $e->getMessage();
    }
} else {
    echo "Aucun tag UID fourni.";
}
?>
