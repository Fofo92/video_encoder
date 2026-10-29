# Recherche dans la liste des tâches

Le champ est visible dans tous les onglets. La saisie filtre immédiatement les
noms et chemins des projets, des sources et des sorties, ainsi que les états
français ou internes. Majuscules et accents ne distinguent pas les résultats.
Plusieurs mots doivent tous être présents, éventuellement dans des colonnes
différentes. La croix du champ efface la recherche.

Depuis Récents, une recherche parcourt tout l’historique ; le champ vide revient
aux quinze dernières tâches. Les onglets d’état conservent leur périmètre et
l’onglet Tous recherche tout l’historique. Le compteur donne le nombre affiché
sur le nombre total de tâches chargées. Le texte saisi est conservé lors des
changements d’onglet et des actualisations.

Les projets sont lus au chargement ou à l’actualisation de la liste. Leur cache
est invalidé par l’identité, la taille ou la date du fichier. Les noms affichés
et chemins des sources partagent cette lecture. Un index normalisé en mémoire
évite toute lecture de projet pendant la frappe et la reconstruction du tableau.
Un projet absent ne bloque pas la recherche par projet, sortie ou état.

Une sélection encore visible est conservée par identifiant ; une sélection
masquée est effacée et ses actions sont désactivées. L’état et la progression
d’une tâche en cours restent conservés quand elle est temporairement masquée.
Lancer la file vise toujours toutes les tâches en attente ; lancer uniquement
la sélection concerne la tâche visible sélectionnée.
