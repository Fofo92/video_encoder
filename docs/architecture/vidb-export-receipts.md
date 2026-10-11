# Comptes rendus des exports pour vidb

L'export d'un projet enregistré écrit, après réussite, un fichier compagnon
`<chemin final>.video_encoder-export.json`. Il décrit la copie finale sondée par
ffprobe, son chemin absolu, sa taille, sa date de modification, les rôles audio
retenus et l'empreinte du document projet lu pour cet export.

Le compte rendu est publié par renommage atomique. Il reste à côté de la vidéo
lorsque le projet est archivé ou l'espace de travail nettoyé. Une erreur de
publication affiche un avertissement sans transformer un encodage réussi en
échec. Aucun compte rendu n'est écrit après un export échoué ou annulé.

Le suivi périodique de vidb lit ces comptes rendus pour rattacher les copies aux
épisodes déjà identifiés. Il contrôle de nouveau le fichier et ses pistes avant
le premier import. Il ne déduit pas la langue du nom de fichier et ne supprime
aucune ancienne copie. Les cas sans identification concordante restent à traiter.

Les exports antérieurs à cette version n'ont pas de compte rendu. Ils nécessitent
une adoption contrôlée à partir du projet et du fichier réellement présents ;
une réexécution de l'encodage n'est pas nécessaire.
