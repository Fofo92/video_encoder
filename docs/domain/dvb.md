# Sous-titres DVB

## Piste déclarée, données présentes et texte exploitable

Ces trois situations doivent être distinguées :

- une piste est déclarée dans les métadonnées du transport ;
- des paquets sont effectivement présents pour son PID ;
- ces paquets permettent de produire des sous-titres affichables.

La présence de paquets ne suffit pas à garantir une extraction OCR utile.
Inversement, l’absence de texte extrait ne prouve pas à elle seule une
absence de sous-titres dans la diffusion : la sélection de piste et le
décodage peuvent aussi être en cause.

La vérification peut combiner FFprobe, un lecteur affichant les sous-titres
DVB d’origine et un passage témoin où du texte est effectivement visible.

## Sous-titres standards et pour malentendants

La sélection actuelle privilégie les sous-titres français non marqués
`hearing_impaired`.

Une piste pour malentendants ne doit pas remplacer silencieusement la piste
standard. La suppression automatique de ses indications sonores ou de
locuteurs ne garantit pas un résultat correct sans relecture.

## Correctif CCExtractor 0.96.6

Un crash reproductible a été localisé dans le traitement du dernier
sous-titre DVB de `process_non_multiprogram_general_loop`.

Le code accédait à `dec_sub.prev->end_time` sans vérifier l’existence de
`dec_sub.prev`. Le correctif ajoute une vérification du décodeur et de ce
pointeur avant cet accès.

Le patch est conservé dans :

`docker/ccextractor/patches/v0.96.6-dvb-null-guard.patch`

Le script de construction l’applique aux sources de la version 0.96.6.
L’image testée porte le nom :

`video-encoder-ccextractor:0.96.6-ocr-fra-diagnostic`

La présence du patch dans le dépôt ne met pas à jour les images Docker
déjà construites. Le lanceur conserve par défaut le nom d’image sans suffixe.
L’image de diagnostic doit donc être sélectionnée explicitement avec
`VIDEO_ENCODER_CCEXTRACTOR_IMAGE`.

Le correctif a supprimé le crash observé. Il ne crée pas de sous-titres
lorsqu’aucun texte n’a été extrait : CCExtractor peut alors terminer avec
le code 10 et supprimer son fichier SRT vide.

## Résultats de diagnostic

Sur « 47 Meters Down », aucun texte exploitable n’a été extrait de la piste
française standard. La piste pour malentendants était visible dans un lecteur.
La cause exacte de l’absence de texte sur la piste standard n’a pas été établie.

Sur « All Her Fault », une piste française standard vérifiée visuellement
a permis une extraction OCR réussie avec l’image corrigée.

Un décalage d’environ dix secondes a été observé lors de l’extraction directe
de l’original. Il n’a pas été retrouvé sur l’extrait testé avec le pipeline
de montage. Aucune compensation générale n’a été ajoutée.

La récupération manuelle de « 47 Meters Down » a finalement été validée
avec une piste vidéo corrigée et une piste audio française, sans version
originale ni sous-titres, conformément au choix de l’utilisateur.
