<?php


session_start();

if (!isset($_SESSION['partie_en_cours'])) {
     $_SESSION['partie_en_cours']=false;
 }
	
	if (!isset($_SESSION['joueur'])) {   // si la variable de session 'joueur' n'exite pas elle est créé
		$_SESSION['joueur'] = [];
        

	}
   echo($_SESSION['joueur']['pseudo']);



    
?>

<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Page de Jeu</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f0f0f0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            flex-direction: column;
        }
        .game-container {
            background-color: #fff;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            text-align: center;
            max-width: 600px;
            width: 90%;
        }
        h1 {
            color: #333;
        }
        p {
            color: #666;
            margin-bottom: 2rem;
        }
        .btn {
            display: inline-block;
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            transition: background-color 0.3s;
        }
        .btn:hover {
            background-color: #45a049;
        }
        
        h4 {
            color:red;
        }
    </style>
</head>
<body>
    <div class="game-container">
        <h1>Bienvenue dans le Jeu</h1>
        
        <?php 
        
        if ( !empty($_SESSION['joueur'])) {

            echo "<h4> le joueur ".$_SESSION['joueur']['pseudo']." est prêt </h4>";
        }
        else {
            echo "<h4> pas de joueur pour l'instant</h4>";
        }
        ?>
        
       <form method = 'post' action = "test_publish.php">
        
        <input type = "submit" class = "btn" value = "lancer le jeu">
        </form>
    </div>
</body>
</html>
