# Commandes et erreurs de la file

Au-dessus des onglets et de la liste, deux barres compactes avec un cadre discret
et des marges verticales réduites indiquent le périmètre. Chaque barre tient sur
une ligne, avec son titre simple à gauche :

- File d’attente : lancer la file, interrompre, arrêter
  après le montage courant, actualiser. Le filtre de recherche ne réduit pas
  le périmètre de lancement de la file.
- Tâche : lancer seulement la sélection, relancer, supprimer la
  tâche, reporter/réactiver, changer sa destination, supprimer son JSON.

La barre Tâche est masquée sans sélection et disparaît si la recherche masque
la tâche choisie. Les deux lignes sont rapprochées comme deux lignes de texte,
avec des icônes de 16 pixels et des bordures explicites indépendantes du rendu
des cadres natifs. Les libellés des icônes sont des verbes courts : Lancer,
Interrompre, Actualiser, Relancer, Supprimer, Reporter/Réactiver et Modifier….
Les exceptions explicites sont Supprimer tâche et JSON… et Arrêter après le
montage en cours. Les infobulles conservent le périmètre détaillé des actions.

Dans l’accueil, les commandes affichent une icône et un libellé. Les actions
grisent et leurs libellés s’actualisent selon les mêmes règles que les boutons
et menus existants. Quitter figure à droite de la barre de menus, sans bouton
en pied de fenêtre ; la protection d’un encodage en cours reste active. Les commandes
qui débordent restent accessibles par le menu d’extension de la barre Qt.

Le panneau de détail d’erreur reste sous la liste, mais n’apparaît que si la
tâche sélectionnée est en échec ou interrompue et porte un message non vide.
Il disparaît si la sélection est masquée, retirée ou si la tâche est rétablie.
Le texte sélectionné pour copie est conservé pendant une actualisation lorsque
le message d’erreur ne change pas.

La dernière actualisation apparaît dans le titre de la fenêtre :
`video_encoder — Montages — dernière actualisation : HH:mm:ss`.
Elle n’occupe plus de ligne au-dessus des commandes.

Une barre d’état en bas indique si un encodage est en cours et le nombre total
de tâches en attente, sans tenir compte de la recherche ou de l’onglet affiché.
Les tâches reportées sont exclues de ce décompte. Le message s’actualise avec
la file et au démarrage ou à l’arrêt du worker, y compris si la tâche en cours
est temporairement masquée par la recherche.
