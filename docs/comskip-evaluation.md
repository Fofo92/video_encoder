# Évaluation Comskip sur des captures réelles

Cet outil produit une proposition éditable, sans encoder ni modifier la source.
Il n'est pas encore raccordé au bouton d'analyse de l'éditeur. Le profil générique
active plusieurs indices Comskip, sans référence à un jingle particulier.
Les bornes humaines servent uniquement à mesurer le résultat après détection.

## Essai Braveheart sur Zeus

Vérifier que `comskip` et `ffprobe` sont disponibles (`command -v comskip` et
`command -v ffprobe`). Comskip est une dépendance externe ; son installation
dépend des paquets disponibles sur la machine. Un exécutable installé ailleurs
peut être désigné par `VIDEO_ENCODER_COMSKIP`.

Depuis le dépôt :

```sh
ruby script/evaluate_comskip.rb \
  --source /commun/to_be_cut/Braveheart.m2t \
  --workspace "$PWD/tmp/braveheart-comskip-evaluation" \
  --reference config/ad_detection/braveheart-novo19.reference.json
```

Le JSON final indique le temps de calcul, le nombre de plages proposées et
l'écart en images par rapport aux deux coupures connues. Ces références partielles
ne permettent pas de calculer la précision globale : il faut aussi regarder les
autres plages proposées et vérifier qu'aucune scène du film n'est écartée.
Le seuil de comparaison est de 25 images, soit une seconde sur cette source.
La correspondance entre les images Comskip et celles de l'éditeur doit être
contrôlée sur la capture réelle, notamment pour les flux TNT discontinus.

Le champ `project` donne le JSON à ouvrir dans l'éditeur pour examiner les
segments. Les bornes extérieures sont par défaut celles de l'analyse ; il faut
les ajuster à l'œuvre, ou fournir `--start-frame N --end-frame N` avec les bornes
inclusives de l'éditeur. Enregistrer ensuite le projet définitif à la destination
souhaitée avant de le mettre en file. Une proposition supprimant tout le
programme est bloquée ; zéro coupure n'est pas une preuve d'absence de publicité.

Relancer la même commande réutilise l'analyse complète si la source, le profil,
la version du moteur et le résultat n'ont pas changé. Un dossier incomplet ou
modifié est refusé ; employer un nouveau nom de dossier pour un nouvel essai.
Les diagnostics restent conservés pour l'évaluation. Leur nettoyage n'est pas
automatique : ne supprimer ce dossier qu'après avoir enregistré le projet
définitif ailleurs et terminé l'examen des résultats.

### Reprise de l'export Braveheart à 50 Hz

Comskip peut exporter les coordonnées à la cadence des champs (50 Hz) alors que
l'éditeur utilise 25 images/s. L'adaptateur accepte ce doublement exact et
convertit les bornes et le nombre d'images vers la cadence moyenne de la source.
Seules les images entièrement comprises dans une plage sont proposées à la
suppression. Les autres rapports de cadence restent bloqués. Cette conversion
ne prouve pas la justesse des raccords sur un flux TNT : le visionnage reste requis.

Pour le dossier déjà calculé puis refusé par l'ancien contrôle de cadence,
ajouter `--recover-complete-output` à la commande d'essai. Cette option exige
le même fichier source, profil et moteur que dans `request.json`, ainsi qu'un
TXT complet et valide ; elle ne relance pas le moteur. Il faut que l'analyse
soit arrêtée avant de demander cette reprise. Une récupération explicite peut
accepter un export complet sans connaître le statut de sortie du processus
initial : elle demeure une proposition à vérifier, jamais une validation de
qualité. Le temps de calcul inconnu est affiché comme `null`.

Le résultat affiche `native_frame_rate`, `project_frame_rate` et
`recovered_output`. Le TXT original est conservé, sans modification. Les reprises
ultérieures vérifient aussi son empreinte. Aucun projet déjà édité n'est écrasé.

## Validation disponible

Les tests automatisés couvrent le format des coupures, les compléments de
segments, les références partielles et la réutilisation contrôlée de l'analyse.
Un essai avec un véritable binaire Comskip sur une source synthétique vérifie
l'exécution et la réutilisation. Ce petit média est classé entièrement comme
publicité : la génération de projet est correctement bloquée. Cet essai ne
mesure pas la qualité de détection sur Braveheart ou sur une autre chaîne.
