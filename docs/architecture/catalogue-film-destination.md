# Identifier le film avant de choisir sa destination

Avant le premier enregistrement d’un nouveau projet, ou le choix d’une sortie
d’encodage, l’application demande à vidb l’identité de l’œuvre à partir du nom
prévu et des sources. Une fiche manquante conduit à la page de recherche
extérieure et de création dans vidb. La fenêtre de montage reste ouverte et
garde ses coupures ; après confirmation dans vidb, reprendre l’enregistrement.

Pour une fiche de film identifiée, la date, les genres et les pays sont affichés.
Le nom canonique est proposé avec le titre original seulement s’il diffère du
titre français. Le résumé est accessible dans les détails. Un dossier de genre
existant est proposé, et le dialogue de destination conserve le choix final.
Le répertoire recherché correspond à l’ensemble des genres du film : par exemple
Western pour un genre, ou Policier, Thriller pour deux genres. Aucun genre n’a
de priorité générale. L’ordre, les accents et la ponctuation des noms de dossiers
ne changent pas l’identité des genres. Si le dossier correspondant est absent ou
ambigu, l’application demande de vérifier le choix dans le dialogue de destination.

Une indisponibilité de vidb laisse possible le choix manuel. Une liaison signée
déjà obtenue est conservée si son actualisation échoue. Aucun reçu supplémentaire
ni fichier d’échange durable n’est ajouté. Le montage continue d’utiliser son
UUID stable et son reçu de fin d’export existant. Les métadonnées de catalogue
affichées restent en mémoire ; elles ne sont pas recopiées dans le JSON du projet.

Le code audio, la vidéo et la confirmation des sources avant mise en quarantaine
restent identiques. Recharger video_encoder après installation du correctif.
