# Découverte de séquences répétées — prototype du 19 octobre 2026

## But et périmètre

Le pilote 6ter cherchait un séparateur connu ; le logo de chaîne détecté par
Comskip est un autre objet. Sur Chien & chat (TF1), Comskip désactive ce dernier
car sa présence détectée est d'environ 1 %. L'affinement par retour du logo ne
peut donc pas aider cette capture.

Ce prototype cherche des séquences visuelles animées répétées dans des extraits,
sans connaître une chaîne, un logo, une couleur ou un texte. Il ne reconnaît pas
encore la fonction publicitaire du motif et ne crée aucun découpage.

## Reproduction

Prérequis de recherche : Python 3, NumPy, FFmpeg et FFprobe. Aucune dépendance
n'est ajoutée au parcours d'encodage. Depuis le dépôt, avec les quatre extraits
déjà fournis par Pascal :

```sh
python3 script/research/repeated_visual_sequences.py \
  tmp/chien-chat-separateurs/depart-1.mp4 \
  tmp/chien-chat-separateurs/depart-2.mp4 \
  tmp/chien-chat-separateurs/reprise-1.mp4 \
  tmp/chien-chat-separateurs/reprise-2.mp4

python3 -m unittest discover -s script/research -p 'test_*.py' -v
```

Le script lit seulement les médias et écrit son rapport JSON sur la sortie
standard. Il refuse les extraits dépassant 120 secondes : la recherche dans une
capture entière, avec une mémoire et un coût de comparaison bornés, reste à
développer. Ne pas lui fournir directement un enregistrement de deux heures.

## Méthode exploratoire

Décodage à 5 images/s, empreintes RGB de 32 × 18 pixels, comparaison de fenêtres
ordonnées de 2 secondes entre extraits. Une paire passe si l'erreur RGB moyenne
quadratique racine est au plus 15 sur l'échelle 0–255 et si chaque fenêtre a un
mouvement d'au moins 2 sur cette échelle. Les fenêtres correspondantes et les
noyaux voisins sont regroupés ; le rapport exige par défaut trois extraits
distincts. L'ordre des images est conservé. Les aplats fixes et les noirs ne
fournissent pas à eux seuls un motif animé.

Ces seuils ont été explorés sur cet échantillon ; ils ne sont pas validés sur
d'autres chaînes. Le script n'utilise ni OCR, ni modèle du jingle, ni bornes
de référence. Les extraits eux-mêmes ont néanmoins été sélectionnés autour des
bornes connues : ce protocole n'est pas une évaluation à l'aveugle sur une capture.

## Mesures sur les quatre extraits TF1

Un groupe est trouvé, avec une occurrence dans chacun des quatre extraits.
Le contrôle visuel l'identifie au séparateur animé « PUB » :

| Extrait | Noyau répétitif proposé, temps relatif à l'extrait |
| --- | --- |
| depart-1 | 11,6–14,6 s |
| depart-2 | 11,6–14,6 s |
| reprise-1 | 8,2–11,6 s |
| reprise-2 | 8,2–11,6 s |

L'erreur RGB des fenêtres appariées est de 0,851 au meilleur cas et de 7,144 en
médiane. Ce sont des distances de ressemblance, pas des probabilités de publicité.

Avec les mêmes paramètres, aucun groupe n'est proposé sur huit passages voisins
ordinaires : pour chaque extrait, les images échantillonnées dans [0,7[ et
[18,28[ secondes, soit 68 secondes au total. Ces passages ont été choisis après
visionnage et excluent les séparateurs ; ils ne mesurent pas le taux de faux
positifs sur une capture entière.

Sept tests automatisés couvrent les séquences décalées, les images fixes, les
séquences indépendantes, le support insuffisant, l'ordre temporel et les entrées
trop courtes. Une répétition de publicité est explicitement laissée sans
classification : la répétition seule ne prouve pas qu'il s'agit d'un séparateur.

## Affinement local ajouté après la première mesure

L'option `--refine-local-boundaries` exige pour l'instant des extraits à 25 fps
constants. Après la recherche à 5 fps, elle aligne une seconde du noyau entre
extraits à 25 fps, puis étend le passage commun image par image tant que la
ressemblance conserve le support requis. Plusieurs occurrences dans un même
extrait ou un alignement insuffisant entraînent une abstention. Le rapport reste
`unverified_shared_run`, sans création d'un projet.

Sur les quatre extraits reçus, le passage commun dure 75 images, soit 3 secondes :

| Extrait | Début inclusif, chronologie de l'extrait | Fin exclusive |
| --- | --- | --- |
| depart-1 | 11,64 s | 14,64 s |
| depart-2 | 11,60 s | 14,60 s |
| reprise-1 | 8,56 s | 11,56 s |
| reprise-2 | 8,56 s | 11,56 s |

Le contrôle visuel des images précédant, suivant et bordant chaque intervalle
retrouve bien l'animation PUB. Ces observations ne mesurent pas l'erreur de coupe
dans le fichier source : il manque encore une correspondance source vérifiée.

Attention aux horodatages : les pistes vidéo reçues commencent respectivement
à 1,00, 0,64, 0,84 et 0,00 seconde dans leurs conteneurs. L'échantillonnage fixe
désormais explicitement son origine à zéro et évite une synchronisation implicite
supplémentaire. Les champs `sampled_start_frame` et `sampled_end_frame_exclusive`
sont des indices dans cette chronologie rééchantillonnée, pas les indices natifs
des images encodées. Un test FFmpeg réel vérifie le cas vidéo retardée/audio dès
zéro ; les onze tests de recherche passent.

Une mesure descriptive du contexte, encore hors classificateur, va dans le sens
des départs et reprises : fraction sombre des premières et dernières lignes de
l'empreinte RGB, mesurée entre 2 et 0,4 secondes avant le motif puis entre 0,4 et
2 secondes après, hors images entièrement noires :

| Extrait | Avant | Après |
| --- | --- | --- |
| depart-1 | 100 % | 6,8 % |
| depart-2 | 100 % | 0,2 % |
| reprise-1 | 0 % | 100 % |
| reprise-2 | 0 % | 100 % |

Cette observation peut conforter une interprétation en séparateur mais dépend
du format de l'œuvre ; une scène sombre ou une publicité au même format peut
contredire cette interprétation. Elle n'est donc pas utilisée pour classifier
automatiquement les répétitions. La distinction publicité répétée/séparateur
reste non résolue par ce prototype.

## Limites et suite nécessaire

Les intervalles indiquent un noyau commun, pas des limites de coupe. Les temps
sont ceux des extraits réencodés ; les positions demandées à FFmpeg pour les
extraire ne constituent pas une preuve de correspondance à l'image près avec
les coordonnées de l'éditeur. Ne pas additionner directement ces temps pour
modifier un projet source.

Il reste à retrouver le début et la fin complets du motif, vérifier la
correspondance avec la source, distinguer les répétitions publicitaires ou de
programme, puis évaluer le procédé sur des fenêtres et captures non utilisées
pour sa conception. Les descripteurs sonores optionnels décrits ci-dessous ne
déterminent pas la classification. Les décisions
ambiguës doivent rester des propositions à vérifier. Aucun changement n'est
apporté au bouton d'analyse ni à la file d'encodage.

## Contexte sonore et validation par retrait d'un extrait

Options supplémentaires : `--characterize-candidates` (exige
`--refine-local-boundaries`) et `--leave-one-clip-out`.

La première calcule des descripteurs spectraux sur le son mono à 8 kHz, avec une
comparaison tolérant un petit décalage temporel. Elle rapporte aussi le contexte
des bordures avant/après le motif et la présence des deux sens de changement.
Ces indications restent descriptives, même si toutes sont positives. Un motif
visuel et sonore répété peut être une publicité ; ce problème n'est pas résolu
par un seuil de ressemblance supplémentaire.

Sur les six paires de séparateurs TF1 : ressemblance sonore médiane 0,686,
minimum 0,662 ; deux paires sont particulièrement proches, 0,964 et 0,988.
Les passages de même durée placés 5 secondes avant et 5 secondes après les motifs
donnent des médianes de 0,322 et 0,342. Ce score n'est pas une probabilité de
publicité. Les sons ne sont pas identiques sur les quatre occurrences, ce qui
invite à ne pas imposer une stricte identité sonore comme condition obligatoire.

Le retrait successif de chaque extrait de la découverte, avec recherche du motif
appris sur les trois autres, donne une correspondance unique dans chaque extrait
retiré : noyaux locaux 12–14 s pour les deux départs et 9–11 s pour les deux
reprises. Le protocole conserve les paramètres existants et ne fournit pas les
bornes de l'extrait retiré au détecteur. Les quatre extraits restent ceux du même
enregistrement connu : cela ne remplace pas une validation sur une autre capture
ou une recherche dans tout un enregistrement.

## Préparation du contrôle sur la source

`script/research/export_indexed_windows.py` prépare des fenêtres autour des
bornes intérieures d'un projet corrigé, pour comparer précisément les images de
la source à celles de l'éditeur. Il sélectionne les images par indice décodé,
sans chercher leur position avec `-ss`, réinitialise les temps des extraits et
écrit un manifeste donnant les indices de début et fin exclusive. Les quatre
fenêtres sont produites en un seul décodage. La durée de ce décodage peut rester
importante sur une longue source ; ce n'est pas un nouveau scan Comskip.

```sh
python3 script/research/export_indexed_windows.py \
  --project projet-corrige.json \
  --output tmp/controle-images-source \
  --radius 250
```

L'outil exige une source de cadence moyenne 25 fps, refuse un dossier existant,
contrôle l'identité du fichier avant/après, conserve les diagnostics et refuse
de clôturer le manifeste si une fenêtre est tronquée. Il n'exporte que la vidéo
pour ne pas prétendre avoir résolu l'alignement audio d'un flux TNT.

Un test FFmpeg réel sur une source synthétique rouge/bleu/vert vérifie la
transition attendue à l'image 25 d'une fenêtre de 50 images. Les tests vérifient
aussi le refus des chevauchements, des sorties déjà présentes et des fenêtres
tronquées. Les 24 tests de recherche passent.

Ce contrôle n'a pas encore été exécuté sur le fichier original Chien & chat,
qui n'est pas accessible dans l'environnement de travail : seuls les extraits
et diagnostics reçus le sont. Le manifeste annonce donc explicitement
`requires_visual_verification` pour l'accord avec les indices de l'éditeur.
L'indice d'une image décodée FFmpeg et celui d'une timeline MLT ne doivent pas
être supposés identiques sur une capture avec discontinuités. Aucun projet de
découpage automatique n'est généré à partir de ces résultats de recherche.

## Diagnostic des exports indexés reçus le 19 octobre à 12:10

Les quatre MP4 reçus contiennent chacun 500 images encodées, mais seulement 499
sont décodées en lecture normale. Leurs durées annoncées sont 19,96 secondes,
avec une cadence moyenne de 12500/499. Le paquet de la dernière image, à 19,96 s,
porte le drapeau discard. Ignorer la liste d'édition MP4 permet de relire les
500 images. L'erreur « Truncated window » était donc trop générale : dans ce cas,
les images sont présentes mais une métadonnée du conteneur masque la dernière.

L'exporteur fixe maintenant explicitement la base de temps 1/25, les PTS N, la
cadence d'encodage 25 fps et la cadence de sortie constante. Cette correction
évite de dépendre des indications de cadence et de durée héritées du flux TNT.

`recover_indexed_windows.py` permet de récupérer les fichiers déjà produits
dans un nouveau dossier : il exige que toutes les images attendues soient
décodables en ignorant la liste d'édition, réencode sans perte et vérifie que
la suite des empreintes de toutes les images décodées reste identique. Il ne
relit pas la capture originale et n'écrase aucun fichier. Une image réellement
absente entraîne un refus, pas une duplication pour atteindre le compte attendu.

```sh
python3 script/research/recover_indexed_windows.py \
  --input tmp/chien-chat-indexed-20261019-120634 \
  --output tmp/chien-chat-indexed-recovered
```

La récupération a été exécutée dans l'environnement de travail sur les quatre
fichiers reçus : 500 images chacun, 20 secondes, 25 fps, origine zéro et empreintes
ordonnées identiques pour toutes les images. Un test supplémentaire reproduit
une liste d'édition raccourcie, constate 49 images lisibles sur 50 encodées et
vérifie la récupération sans changement de pixels ni d'ordre. Les 25 tests de
recherche passent.

La découverte puis l'affinement ont été relancés sur ces fenêtres indexées,
avec les paramètres existants. Les limites du motif partagé sont :

| Fenêtre | Début inclusif local | Fin exclusive locale | Repère déduit dans les indices décodés source |
| --- | --- | --- | --- |
| departure-1 | 251 | 326 | OUT 74 596 |
| departure-2 | 250 | 325 | OUT 120 822 |
| resume-1 | 175 | 250 | IN 83 516 |
| resume-2 | 175 | 250 | IN 130 226 |

Le calcul utilise le début du motif moins une image pour OUT, et sa fin exclusive
pour IN. Le contrôle visuel des images adjacentes retrouve bien le passage du
film au séparateur et du séparateur au film. Ces quatre repères concordent avec
le projet corrigé par Pascal, à une image près au premier départ (OUT manuel
74 595). Cela donne un accord local sur cette capture ; les fenêtres étaient
centrées sur les bornes manuelles connues. Ce n'est toujours pas une mesure de
détection à l'aveugle dans toute la capture ni une preuve d'identité globale
des indices FFmpeg et MLT en présence de discontinuités.

### Full-source search for an already learned motif

`script/research/scan_learned_sequence.py --source RECORDING --clips CLIP1 CLIP2 CLIP3 CLIP4`
learns a two-second moving core from the observation clips, then streams the full
source at 5 fps in bounded blocks. Overlap preserves matches crossing block
boundaries. No corrected project, expected cut positions or channel template is
accepted. A changing source, ambiguous motif or decoder error stops the run.
The original recording is read only. Requires Python/NumPy and FFmpeg.

This is **not blind full-recording discovery**: observation clips were selected
manually. It tests the learned motif's presence and additional matches throughout
the recording. A repeated advert can match; the output cannot determine which
side of a match to retain. Report times use the FFmpeg resampled timeline and
must not be used as verified editor frame indices. No project or cuts are emitted.

The streaming matcher has synthetic checks for source edges, overlapping blocks,
blocks shorter than a motif, temporal reversal and static sequences. A smoke test
on recovered Chien & chat departure-1 finds its core at 10 seconds. This smoke
test uses an observation clip and is not independent validation. The full original
capture is available only on Zeus; its full-source result is still pending.

### Résultat du balayage complet sur Zeus et affinement

Le 19 octobre, Pascal a exécuté le scanner sur Chien & chat : 35 995 images à
5 fps, 12 occurrences. Quatre noyaux sont à l'intérieur des bornes extérieures
20 243–157 947 : 2 984,4 s, 3 338,2 s, 4 833,4 s et 5 206,6 s. Les huit autres
sont avant ou après l'œuvre et n'ont pas été classifiés. Les quatre emplacements
attendus sont retrouvés, mais ce résultat n'évalue pas les limites de coupe.

`refine_source_occurrences.py` accepte ce rapport et les deux bornes extérieures,
jamais les coupes corrigées. Il extrait en un décodage des fenêtres de 14 secondes
centrées autour des noyaux trouvés, sur une chronologie FFmpeg explicitement
rééchantillonnée à 25 fps. Il exige une source de cadence moyenne 25 fps, un
nouveau dossier, des fenêtres ordonnées sans chevauchement et un motif unique
soutenu par toutes les fenêtres. Il conserve le manifeste et les diagnostics,
contrôle l'identité de la source et refuse les fenêtres tronquées.

L'extension locale du motif commun produit ses limites inclusives/exclusives.
Elle ne décide ni « départ » ni « reprise » et ne crée aucun projet. Les indices
sont ceux de la chronologie rééchantillonnée, pas des indices d'éditeur validés.
L'accord avec les corrections humaines doit être évalué après l'extraction.

```sh
python3 script/research/refine_source_occurrences.py \
  --scan-report tmp/chien-chat-recherche-20261019-122501/resultat.json \
  --start-frame 20243 --end-frame 157947 \
  --output tmp/chien-chat-affinement-source
```

### Correction des coordonnées après le premier affinement complet

Le premier résultat sur Zeus donnait des repères de coupe 74 609, 83 529,
120 835 et 130 239 contre les corrections 74 595, 83 516, 120 822 et 130 226.
Les écarts de +14/+13/+13/+13 images indiquent une différence de coordonnées ;
ils ne justifient pas une soustraction fixe codée en dur.

L'extracteur retire désormais `fps=25:start_time=0` AVANT `trim`. Les fenêtres
sont sélectionnées par indice d'image décodée ; les temps et la cadence sont
réinitialisés APRÈS cette sélection, sans duplication préalable. Les secondes du
scanner servent seulement à localiser approximativement des fenêtres de contexte.
Leurs limites affinées sont calculées dans les images décodées de la source.
Les champs correspondants sont renommés `first_decoded_frame`,
`motif_start_decoded_frame` et `motif_end_decoded_frame_exclusive`.

Un test FFmpeg conserve volontairement une origine vidéo décalée de 0,52 seconde :
l'ancien filtre introduit 13 images supplémentaires (38 images pour 25 réelles),
le filtre corrigé conserve les 25 images réelles. Ce test démontre le mécanisme,
pas son origine exacte dans Chien & chat. Le rapport conserve maintenant aussi
les métadonnées de début du conteneur et de la piste vidéo. Une nouvelle exécution
sur la source originale est nécessaire pour vérifier les écarts ; aucune égalité
globale entre indices décodés et indices de l'éditeur n'est supposée.

### Affinement corrigé vérifié sur Zeus

Pascal a exécuté le correctif 725dd2c sur la source originale. Les limites du
motif sont [74 597,74 672[, [83 441,83 516[, [120 823,120 898[ et
[130 151,130 226[. En utilisant le début moins une image pour les deux départs
et la fin exclusive pour les reprises, les quatre écarts aux corrections manuelles
sont +1/0/0/0 image. Le calcul n'avait pas reçu les coupes intérieures.
Les métadonnées annoncent un début vidéo à 71321,635156 s et un début conteneur
à 71320,559156 s : leur différence de 1,076 s n'explique pas, à elle seule,
le décalage de 13 images constaté dans la précédente chronologie rééchantillonnée.
Le correctif évite cette dépendance aux temps pour la sélection des images.

### Découverte sans extraits modèles : nouveau prototype

```sh
python3 script/research/discover_source_sequences.py \
  --source '/commun/to_be_cut/Chien & chat.m2t' \
  --output tmp/chien-chat-decouverte-source
```

Cette commande n'accepte ni extrait, ni projet de référence, ni positions de coupe,
ni bornes extérieures, ni modèle de chaîne. Elle décode à 5 fps vers un cache RGB
sur disque (environ 62 Mo pour deux heures), puis indexe des descripteurs spatiaux
et temporels. Les rapprochements indexés sont vérifiés sur dix images RGB
ordonnées (deux secondes), avec les seuils visuels du prototype existant. Les
fenêtres statiques sont écartées. Trois occurrences séparées sont exigées.

L'index est approximatif et déterministe, pas une comparaison exhaustive.
Les limites de taille des groupes indexés et de nombre de comparaisons sont
signalées dans le rapport ; leur absence ne prouve pas un rappel complet.
Une publicité ou une séquence de programme répétée peut satisfaire les critères.
Le programme n'en déduit ni la fonction de séparateur ni une coupe, et ne crée
aucun projet. Les temps restent ceux du rééchantillonnage ; un affinement par
indices décodés demeure nécessaire ensuite. Un nouveau dossier est exigé,
l'identité de la source est contrôlée et une limite de recherche de six heures
évite une taille non bornée du cache.

Vérification locale : les quatre extraits vidéo reçus, concaténés uniquement sous
forme d'empreintes, produisent un seul groupe avec les quatre noyaux du motif.
Il s'agit encore d'extraits sélectionnés par l'humain ; la découverte sur le
fichier entier sans modèle reste à exécuter sur Zeus. Les tests synthétiques
couvrent répétitions sans modèle, support insuffisant, source statique, entrée
courte et signalement du plafond de comparaisons.

### Retour du premier essai sans modèle et sélection d'un groupe

L'exécution de 6d131d1 sur Zeus trouve cinq groupes. Le deuxième contient douze
occurrences, dont les quatre noyaux attendus dans l'œuvre. Le premier groupe
contient dix-sept ressemblances non classifiées. Les plafonds de comparaisons
(500 000) et de taille des groupes indexés sont atteints : le résultat n'est pas
exhaustif. La fréquence seule ne fournit donc pas un classement sémantique fiable.

L'affinement accepte désormais explicitement `--candidate 2` avec le rapport de
découverte, les bornes extérieures et un nouveau dossier de sortie. L'absence de
choix, un numéro hors limites ou une source modifiée depuis le rapport entraîne
un refus. La sélection est inscrite dans le manifeste, ainsi que le fait que la
recherche initiale a atteint ses plafonds. Les anciens rapports du scanner à
motif appris restent compatibles sans option de sélection.

```sh
python3 script/research/refine_source_occurrences.py \
  --scan-report DOSSIER_DE_DECOUVERTE/resultat.json --candidate 2 \
  --start-frame 20243 --end-frame 157947 --output NOUVEAU_DOSSIER
```

Cette sélection est une validation explicite pour cet essai, pas une règle disant
que le deuxième groupe est toujours un séparateur. L'affinement extrait ses
fenêtres sur la source originale ; il ne relance pas la découverte. Les limites
communes sont proposées sans générer de projet d'encodage.

### Réutilisation du cache de découverte

```sh
python3 script/research/discover_source_sequences.py \
  --source '/commun/to_be_cut/Chien & chat.m2t' \
  --reuse-cache DOSSIER_DE_DECOUVERTE --output NOUVEAU_DOSSIER \
  --max-pairs 2000000 --max-bucket 512
```

L'outil réutilise les empreintes RGB existantes en lecture seule. L'identité du
fichier source, le statut complet et la longueur exacte du cache sont contrôlés.
Les nouveaux caches portent une empreinte SHA-256, vérifiée avant et après la
recherche. Le premier cache créé sur Zeus n'en portait pas : sa reprise indique
`legacy_cache_no_original_digest`, sans prétendre prouver son intégrité historique.
Le nouveau manifeste enregistre une empreinte pour les reprises ultérieures.

La clôture du cache précède la recherche de motifs : une interruption de cette
dernière laisse ainsi le décodage réutilisable. Les sorties sont dans un nouveau
dossier et peuvent référencer le cache précédent sans le recopier. Conserver ce
cache tant que ces sorties doivent pouvoir être rejouées. Augmenter les plafonds
permet plus de comparaisons, sans rendre l'index approximatif exhaustif.
