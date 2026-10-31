# Suppression de projet

Projets → Supprimer un projet retire les fichiers du montage, indépendamment
des tâches de la file. Par défaut, seul le JSON est concerné. L'option dépendances
inclut les sorties encodées connues des tâches et les vidéos de même nom
(.mkv, .m4v, .mp4), ainsi que leurs reçus .video_encoder-export.json.
Les captures sources restent conservées et les workspaces ne sont jamais effacés.

Une première étape choisit l'étendue, puis une confirmation, négative par défaut,
énumère tous les fichiers. Les fichiers sont déplacés dans
`.video_encoder_trash/UUID` à côté du projet. Le manifest.json associe chaque
chemin initial à son emplacement de récupération. Aucun fichier n'est effacé
définitivement ; ne pas purger ce dossier sans vérifier son contenu.

Le service Ruby contrôle les tâches sous transaction SQLite immédiate, comme
le déplacement de projet. Les statuts running, queued et deferred bloquent
la suppression. Les fichiers partagés avec d'autres tâches/projets connus de
la file sont protégés. Un workspace existant bloque l'opération. Le menu est
désactivé tant qu'un éditeur est ouvert dans cette instance.

Le plan signé par l'identité, la taille et les dates des fichiers est recalculé
après confirmation. Un changement invalide la confirmation. Une erreur de
déplacement restaure les fichiers déjà déplacés. Le journal de récupération
reste disponible. Les tâches terminées et leur historique ne sont pas supprimés.

La connaissance des références partagées se limite aux projets de la file et
aux sources du projet choisi ; les projets externes absents de la file ne
peuvent pas être inventoriés. La récupération conserve donc les fichiers.

Le menu Montage reste l'accès textuel et clavier aux actions du cycle ; la
barre d'icônes réutilise ses QAction. Le menu Sources ne duplique plus Nouveau
montage et l'examen des captures s'appelle Vérifier les sources avant quarantaine.
