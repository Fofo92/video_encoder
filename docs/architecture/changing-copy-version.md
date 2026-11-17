# Changer de version

Le menu Montage → Changer de version… regroupe deux parcours :

- Depuis les sources d’un projet JSON : VF, VM et VMST, avec le réencodage existant.
- Depuis une copie MKV : VOST avec une piste originale choisie et des sous-titres
  français déjà incrustés. Aucun encodage vidéo ou audio ; les autres pistes sont
  retirées de la nouvelle copie.

Le second parcours exige deux confirmations indépendantes : VO vérifiée à
l’écoute, et sous-titres français incrustés vérifiés à l’image. Ni qaa ni l’absence
de piste de sous-titres ne constituent cette preuve. Les sous-titres incrustés ne
peuvent pas être détectés par la liste des pistes.

Le dernier bouton est « Ajouter à la file d’attente ». La préparation ne démarre
pas de worker : elle enregistre un projet video_encoder.copy_version et utilise
la file trim_export existante. Un worker déjà lancé traite les tâches en série.

Le fichier source et son projet sont conservés. La destination est nouvelle et
les créations du JSON et du MKV refusent tout écrasement, y compris les liens
symboliques. Une identité taille/date/inode/périphérique contrôle la source à la
préparation et à l’exécution. Le résultat doit avoir une vidéo, un audio, aucun
sous-titre séparé, et une durée compatible avant publication atomique.

Le reçu habituel inclut version_change, avec la confirmation visuelle et la
piste audio explicitement choisie. Après import de l’inventaire, vidb crée une
nouvelle copie VOST ; la copie précédente et les états de visionnage restent
inchangés. Les défauts déclarés de la copie source connue de vidb sont conservés.
La qualification ne dépend pas d’un renommage ou d’une édition de la fiche.

Depuis vidb, « Changer de version… » sur une copie transmet un ticket signé lié
au compte, à la fiche et à la copie. Chaque préparation génère un nouvel
identifiant de projet, même si le même lien est réutilisé. Le chemin
est résolu par la passerelle authentifiée ; un changement de source est refusé.
Le menu Montage de vidb propose aussi l’entrée générique de video_encoder.

Les projets de changement de version peuvent être repris par le menu Montage,
et sont reconnus par les outils habituels de déplacement, suppression et suivi
des sources. Ils ne nécessitent pas la capture initiale du montage.

Ce profil ne fabrique pas de sous-titres incrustés à partir d’une piste séparée.
Pour une copie sans sous-titres incrustés, la VOST n’est pas proposée par ce
parcours ; la sélection des pistes VF/VM/VMST reste disponible depuis le projet.
