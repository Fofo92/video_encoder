# Montage manuel

## Montage manuel et arrêt du pilote publicitaire

Le parcours courant est : ouvrir une source ou un projet, poser les plages
IN/OUT à conserver, ajuster les raccords, enregistrer et mettre en file d’encodage.

Les commandes « Analyser les publicités », « Créer avec coupures » et
« Séparateurs répétés » ont été retirées de l’éditeur, avec leurs processus,
dialogues et états d’attente spécifiques. Aucune dépendance Comskip ou NumPy
n’est nécessaire pour ce parcours manuel.

Les projets JSON existants restent ouvrables et modifiables, y compris ceux
issus des essais. La file et les fichiers vidéo ne sont pas modifiés par cette
simplification. Aucun nettoyage de sources ou de caches existants n’est lancé.

Les approches expérimentales, leurs scripts, leurs tests et leurs rapports sont
conservés dans la branche [archive/advertising-detection-experiments](https://github.com/Fofo92/video_encoder/tree/archive/advertising-detection-experiments),
au commit `4c92356f48d250e0f3a4d9af1674eb7bfb38dd7a`.
Ils ne sont pas importés dans cette version simplifiée de `main`.
Le helper de compatibilité des anciens dossiers d’analyse reste couvert par
les tests de sauvegarde et de nettoyage.

La CI vérifie le parcours manuel, les projets et la file avec Qt et MLT.
La campagne expérimentale de détection ne fait plus partie de ses contrôles.
