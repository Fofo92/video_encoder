# Liaison du projet à vidb

Après installation du correctif côté vidb, sa commande
`bin/install-encoder-project-bridge https://zeus.fodiman.fr` configure les deux côtés
sur Zeus. Lancer cette commande depuis le dépôt vidb, avec le compte qui utilise
video_encoder. La configuration client privée se trouve dans
`~/.config/video_encoder/vidb.json`, ou sous XDG_CONFIG_HOME ; le chemin peut être
remplacé par VIDEO_ENCODER_VIDB_CONFIG. Aucun nouveau paquet n’est requis.

L’enregistrement d’un montage lui donne un UUID stable. Pour les projets destinés
à `/videos`, la liaison activée demande à vidb une identification, avec un délai
réseau court. Le projet est écrit avant la demande et reste enregistré si le service
est indisponible. Les tests et les écritures hors vidéothèque n’appellent pas vidb.

Un lien certain est conservé dans le projet et affiché dans la barre d’état.
Le menu Montage → Identifier l’œuvre dans vidb permet de reprendre une demande.
Avant l’encodage, si une validation manque, video_encoder propose d’ouvrir la file
vidb ou d’encoder sans association. Ouvrir la file suspend seulement le lancement
de cet export ; il reste à relancer après validation. Aucun encodage déjà actif
n’est interrompu. Les créations de fiches manquantes restent traitées dans vidb.

La lecture et la réécriture par l’éditeur conservent `project_id` et `vidb`.
Un nouveau montage reçoit une nouvelle identité ; changer les coupures ou déplacer
le même projet conserve son lien. Les reçus de sortie reprennent l’UUID ainsi que
les seuls champs de liaison `record_id` et `binding_token`. Ils ne contiennent pas
le secret de communication avec vidb. Les anciens projets et reçus restent acceptés.

Le serveur valide les choix avec le même moteur de décisions sur un cas que l’atelier
de consolidation. Il conserve une trace, impose un seul choix par projet et vérifie
que les fiches examinées sont toujours cohérentes. Le fichier n’est déclaré présent
qu’après son export et son contrôle réel. Cette intégration ne modifie aucune option
d’encodage, aucun raccourci de découpage ni la ShuttleXpress.
