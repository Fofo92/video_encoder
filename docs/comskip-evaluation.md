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

Lorsque `--start-frame` et `--end-frame` sont tous deux fournis, les deux bornes
sont désormais verrouillées : les plages détectées qui touchent IN ou OUT sont
ignorées en entier, sans raccourcir le programme à ces extrémités. Seules les
coupures strictement intérieures sont appliquées. Si une seule plage détectée
recouvre toute l'enveloppe manuelle, la proposition est bloquée pour examen.
Le résultat annonce `outer_bounds_locked: true` et les plages ignorées dans
`ignored_boundary_intervals`. Cela ne garantit pas que les coupures intérieures
soient précises ou complètes.

Le projet est alors nommé `proposal-locked-IN-OUT.json`, pour conserver les
propositions antérieures et les modifications manuelles. Les anciennes analyses
restent réutilisables : ce verrouillage ne demande aucun nouveau calcul Comskip.

### Deuxième essai : 9-1-1, S05 E15

Le projet nommé `_comskip.json` fourni initialement provenait du bouton de
l'interface, qui utilise encore le détecteur historique. Ne pas attribuer sa
pause manquée à Comskip. Le véritable essai Comskip lancé ensuite en terminal
a retrouvé les deux pauses en environ 414 secondes.

La référence finale est `config/ad_detection/911-s05e15.reference.json` :
13 405–30 021, 37 962–70 082 et 79 547–92 044. Elle remplace le premier JSON
manuel incomplet à deux segments. Les erreurs de bornes publicitaires Comskip
sont [1, -510] et [-5, -147] images : les reprises sont trop précoces de
20,40 secondes et 5,88 secondes. Le verrouillage corrige la perte aux extrémités
de l'œuvre, pas ces imprécisions intérieures. Aucun décalage spécifique à cet
épisode n'est appliqué au moteur.

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

### Référence corrigée du 19 octobre 2026

Le projet corrigé par Pascal remplace les premiers repères : segments conservés
14 073–105 331, 110 621–171 215 et 176 612–271 036 (bornes inclusives).
La référence JSON conserve ces segments et l'enveloppe de l'œuvre à des fins
d'évaluation uniquement. Ces champs ne pilotent pas Comskip et ne fixent pas
automatiquement les bornes du projet proposé.

Avec cette référence finale, une des deux plages intérieures respecte la
tolérance : erreurs de bornes [1, 0] puis [0, 78] images. La reprise après la
deuxième pause supprime donc 78 images de film (3,12 secondes). La fin du segment
principal proposé dépasse de 1 033 images (41,32 secondes) la fin validée.
Ce bilan corrige le premier rapport fondé sur les repères préliminaires ; il
ne constitue pas une amélioration de la détection. Ne pas appliquer un décalage
constant de 78 images aux autres captures pour faire passer ce cas.

Les tests automatisés couvrent le format des coupures, les compléments de
segments, les références partielles et la réutilisation contrôlée de l'analyse.
Un essai avec un véritable binaire Comskip sur une source synthétique vérifie
l'exécution et la réutilisation. Ce petit média est classé entièrement comme
publicité : la génération de projet est correctement bloquée. Cet essai ne
mesure pas la qualité de détection sur Braveheart ou sur une autre chaîne.
