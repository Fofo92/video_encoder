# Commandes et erreurs de la file

Au-dessus des onglets et de la liste, deux groupes indiquent le périmètre :

- File d’attente — toutes les tâches : lancer la file, interrompre, arrêter
  après le montage courant, actualiser. Le filtre de recherche ne réduit pas
  le périmètre de lancement de la file.
- Tâche sélectionnée : lancer seulement la sélection, relancer, supprimer la
  tâche, reporter/réactiver, changer sa destination, supprimer son JSON.

Dans l’accueil, les commandes affichent une icône et un libellé. Les actions
grisent et leurs libellés s’actualisent selon les mêmes règles que les boutons
et menus existants. Quitter reste séparé en pied de fenêtre. Les commandes
qui débordent restent accessibles par le menu d’extension de la barre Qt.

Le panneau de détail d’erreur reste sous la liste, mais n’apparaît que si la
tâche sélectionnée est en échec ou interrompue et porte un message non vide.
Il disparaît si la sélection est masquée, retirée ou si la tâche est rétablie.
Le texte sélectionné pour copie est conservé pendant une actualisation lorsque
le message d’erreur ne change pas.
