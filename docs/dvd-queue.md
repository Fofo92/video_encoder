# DVD : préparer, nommer et encoder un titre entier

## Parcours

Depuis l’accueil, **Préparer un DVD…** (également dans le menu Sources) :

1. Analyser le disque dans `/dev/sr0`, puis choisir un titre et sa durée.
2. Indiquer le nom de l’œuvre ou de la série. Pour une série, préciser la saison
   et l’épisode correspondant à ce titre. L’ordre des titres DVD ne prouve pas
   l’ordre des épisodes ; cette correspondance est à vérifier pour chaque titre.
3. Copier le titre. Une copie MKV sans réencodage, avec toutes les pistes, est
   enregistrée sous `/commun/to_be_cut/DVD/<identifiant>/`. Après la copie,
   l’encodage utilise exclusivement ce fichier local.
4. Confirmer les pistes VF, VO et la piste de sous-titres. La langue et le nombre
   de paquets sont affichés. Le choix initial privilégie l’unique VF ordinaire,
   l’unique langue étrangère ordinaire et la piste française la plus remplie.
   Une ambiguïté audio exige un choix ; aucune langue `qaa` n’est inventée.
5. Identifier ou créer la fiche dans le parcours vidb existant. Le rattachement
   doit être confirmé. Les métadonnées de la fiche proposent le classement et
   les noms français/originaux de l’œuvre, de la série et de l’épisode.
6. Vérifier le titre et la destination, puis confirmer l’ajout à la file.
   Le JSON est sauvegardé à côté du futur MKV avant l’ajout de la tâche.
   La file n’est pas démarrée par cette action. Si elle tourne déjà, elle pourra
   traiter la nouvelle tâche à son tour.

Répéter pour les autres titres utiles du disque. Il n’est pas nécessaire de
laisser le disque inséré une fois leurs copies locales terminées.

## Encodage

Le projet `video_encoder.dvd_project`, version 2, utilise le type de tâche
`trim_export` existant : démarrage, interruption, reprise, modification de
la destination et déplacement du projet passent par les actions habituelles.
Les montages TV conservent leur exporteur.

Le premier profil, `dvd-pal-hevc-v1`, reprend l’essai validé : DVD PAL 25 images/s,
HEVC NVENC qualité 23, hauteur maximale 720, désentrelacement adaptatif,
AAC 160 kbit/s par piste. Il requiert HandBrakeCLI avec NVENC fonctionnel et
FFmpeg avec l’entrée `dvdvideo`, ainsi que les dépendances de la file actuelle.
Ce profil refuse les sources NTSC ; il ne traite ni Blu-ray ni montage de
plusieurs titres dans un même fichier.

HandBrake encode exclusivement vidéo et audio. FFmpeg réintègre ensuite la
piste VobSub sélectionnée depuis la copie locale, sans OCR ni décodage des
sous-titres par HandBrake. Aucun décalage arbitraire n’est ajouté. La durée,
les pistes finales et les langues sont contrôlées avant publication du MKV.
La synchronisation réelle reste à vérifier sur le premier titre du disque.

Le reçu `.video_encoder-export.json` réutilise le format habituel, l’identifiant
stable du projet, la liaison signée à la fiche et les rôles VF/VO confirmés.
L’import des fichiers terminés dans vidb peut ainsi rattacher le MKV à la fiche
existante. La préparation seule ne modifie pas les états enregistré/disponible.
L’inventaire des DVD physiques reste distinct du rattachement du MKV terminé.

## Reprise et conservation

- Une copie locale est conservée après annulation, échec ou succès. Le bouton
  **Reprendre une copie locale déjà terminée…** relit son `dvd-source.json`.
  Ces MKV sources ne sont pas mis automatiquement en quarantaine.
- Après un échec d’ajout à la file, **Projets → Ouvrir un projet…** permet de
  reprendre l’ajout du JSON DVD sauvegardé. Un projet déjà en attente/en cours
  n’est pas ajouté une deuxième fois par ce parcours.
- Pour une tâche en échec ou interrompue, utiliser **Relancer** dans la file.
  Les fichiers intermédiaires sont recréés ; la source locale reste intacte.
- Les projets et sorties existants ne sont pas écrasés. Les liens symboliques
  cassés sont eux aussi considérés comme des destinations occupées.
- Un projet DVD représente un titre entier et s’ouvre dans le parcours DVD,
  pas dans l’éditeur de coupures TV.

## Vérification avant utilisation

`bin/check`, puis un seul titre du disque de référence : vérifier le nom proposé,
la fiche vidb, les deux langues audio et les sous-titres au début, au milieu et
à la fin. Vérifier ensuite le rattachement après l’import habituel dans vidb.
Les tests automatisés simulent les outils multimédias ; ils ne remplacent pas
cet essai avec le lecteur et la carte NVIDIA de Zeus.
