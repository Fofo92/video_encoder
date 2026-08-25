# Architecture de déploiement

## Objectif

Ce document décrit la répartition envisagée des responsabilités entre les différentes machines participant à l’écosystème de `video_encoder`. Il distingue notamment :

- le stockage des fichiers multimédias ;
- les traitements audiovisuels ;
- le catalogue géré par `vidb` ;
- la consultation et la lecture près du téléviseur.

L’objectif est de retenir une architecture simple pour le développement actuel, sans empêcher une distribution ultérieure des services.

## Contexte matériel

### Poste de traitement

Le poste principal fonctionne sous Debian sur une architecture `amd64`. Il dispose notamment :

* d’un processeur AMD Ryzen 9 5900X à 12 cœurs et 24 processeurs logiques ;
* de 64 Gio de mémoire vive ;
* d’une carte graphique NVIDIA GeForce GTX 1660 compatible NVENC ;
* d’environ 16 To de stockage consacrés aux fichiers vidéo.

Les médias sources et produits étant stockés sur cette machine, elle constitue l’emplacement naturel des traitements réalisés par FFmpeg, MLT, CCExtractor et Tesseract.

### Serveur Synology

Le serveur Synology DS415+ dispose :

* d’un processeur Intel Atom C2538 à quatre cœurs cadencés à 2,4 GHz ;
* de 8 Gio de mémoire vive.

Il peut héberger des services applicatifs modérés, des données et des sauvegardes. Sa puissance et son ancienneté ne le destinent toutefois pas aux traitements audiovisuels lourds. Son rôle exact dans l’hébergement de `vidb` reste à étudier.

### Poste de lecture

Un poste dédié pourra ultérieurement être installé près du téléviseur.

Il devra privilégier :

* le silence ;
* une faible consommation électrique ;
* un faible encombrement ;
* une lecture fluide des formats produits ;
* un accès réseau à la médiathèque et à `vidb`.

Ce poste constituera principalement un client de consultation et de lecture. Il n’a pas vocation, à ce stade, à exécuter la chaîne d’encodage.

## Architecture retenue à court terme

## Répartition des responsabilités

## Distribution de CCExtractor

La conversion des sous-titres DVB repose sur une chaîne associant CCExtractor, Tesseract et les données linguistiques françaises.

Cette chaîne a une influence directe sur :

- le décodage des sous-titres DVB ;
- l’interprétation de leur chronologie ;
- la gestion des ruptures de PTS ;
- la segmentation des entrées SRT ;
- la qualité du texte reconnu.

Sa distribution doit donc permettre d’identifier précisément l’environnement ayant produit un résultat validé.

### Décision retenue

CCExtractor avec OCR français est distribué dans une image Docker dédiée.
Cette conteneurisation reste limitée à CCExtractor et à ses dépendances :

- CCExtractor ;
- Tesseract ;
- Leptonica ;
- GPAC ;
- le modèle linguistique français de Tesseract ;
- les bibliothèques nécessaires à leur exécution.

Le reste de `video_encoder` demeure exécuté directement sur le poste Debian.
FFmpeg, FFprobe, MLT et l’accès aux médias ne sont pas déplacés dans le conteneur.

Cette solution a été retenue après examen de l’installation native sous Debian 13.
CCExtractor n’est pas fourni par les dépôts utilisés et sa
construction nécessite notamment GPAC, qui n’y est pas disponible sous la
forme d’un paquet de développement. Une installation locale aurait donc
également nécessité le maintien d’une chaîne de construction spécifique.

L’image Docker offre ici une frontière de distribution plus explicite et
permet de conserver ensemble les composants de la chaîne OCR validée.

### Construction des images

Le script `bin/build_ccextractor_image` construit une image à partir d’une
version explicitement prise en charge :

```shell
bin/build_ccextractor_image 0.96.6
```

Les versions actuellement reconnues sont :

- `0.96.5`, associée au commit `477307e438a6089314f3c1d7fe083943220e90fa` ;
- `0.96.6`, associée au commit `185631dcb0217b4ad09d43009cb69f0593996a5d`.

Le script :

1. clone le tag correspondant depuis le dépôt officiel de CCExtractor ;
2. vérifie que son commit correspond à la valeur attendue ;
3. construit l’image OCR fournie par le projet amont à partir des sources locales vérifiées ;
4. ajoute les données linguistiques françaises de Tesseract ;
5. produit une image portant un tag versionné.

L’image courante est :

```text
video-encoder-ccextractor:0.96.6-ocr-fra
```

La version 0.96.6 nécessite un correctif d’empaquetage local, conservé dans :

```shell
docker/ccextractor/patches/v0.96.6-version.patch
```

Ce correctif ne modifie pas le traitement des sous-titres. Il corrige uniquement le numéro de version encore déclaré comme `0.96.5` dans les sources du tag `v0.96.6`.

### Exécution

Le lanceur `bin/video_encoder_ccextractor` adapte l’interface de l’exécutable conteneurisé à celle attendue par `video_encoder`.

Il exécute un conteneur éphémère :

- sans accès réseau ;
- avec l’identité de l’utilisateur courant ;
- avec le seul workspace nécessaire monté dans le conteneur ;
- avec suppression automatique du conteneur après son exécution.

La CLI peut utiliser ce lanceur grâce à la variable  `CCEXTRACTOR_EXECUTABLE` :

```shell
CCEXTRACTOR_EXECUTABLE="$PWD/bin/video_encoder_ccextractor" \
  bin/video_encoder export projet.json --output montage.mkv
```

Le chemin du workspace est normalement déduit de l’argument de sortie transmis à CCExtractor.
La variable `VIDEO_ENCODER_WORKSPACE` reste acceptée pour les  usages qui doivent le fournir explicitement.

### Changement de version et retour arrière

L’image utilisée par le lanceur peut être remplacée sans modifier le code :

```shell
VIDEO_ENCODER_CCEXTRACTOR_IMAGE=\
video-encoder-ccextractor:0.96.5-ocr-fra-reference \
CCEXTRACTOR_EXECUTABLE="$PWD/bin/video_encoder_ccextractor" \
  bin/video_encoder export projet.json --output montage.mkv
```

Cette possibilité permet :

- de comparer deux versions ;
- de diagnostiquer une éventuelle régression ;
- de revenir temporairement à une chaîne OCR déjà validée ;
- de tester une image candidate avant de modifier l’image par défaut.

### Validation

Les images 0.96.5 et 0.96.6 ont été comparées sur le transport de sous-titres du projet d’acceptation multi-source.

Les fichiers SRT produits sont identiques octet par octet et possèdent l’empreinte SHA-256 suivante :

```text
dee936a98d53710fa5af98c0832df4c32f6373a6b3682d6bd8c7986dec0ed7eb
```

L’export complet réalisé avec l’image 0.96.6 a également été vérifié :

- vidéo HEVC ;
- piste audio française ;
- piste audio en version originale ;
- sous-titres français au format SubRip ;
- workspace supprimé après le succès ;
- résultat validé par visionnage.

Une nouvelle image ne doit remplacer la version courante qu’après ces mêmes contrôles

## Principes de conception

L’architecture de déploiement respecte les principes suivants.

### Traitements au plus près des médias

Les opérations qui lisent ou produisent des fichiers volumineux sont exécutées sur la machine qui héberge la médiathèque.

Cette proximité limite les transferts réseau et évite de rendre le pipeline dépendant de la disponibilité d’un stockage distant.

### Séparation entre pilotage et exécution

La construction d’un projet, la demande d’un export et l’exécution du traitement constituent des responsabilités distinctes.

À terme, `vidb` pourra demander un export sans devoir exécuter directement
FFmpeg, MLT ou CCExtractor. Le worker de `video_encoder` restera responsable
des traitements audiovisuels.

### Dépendances explicites
Les chemins des exécutables externes et les paramètres propres à
l’environnement doivent rester configurables.

Le cœur de `video_encoder` ne dépend pas directement de Docker : il appelle
l’exécutable défini par `CCEXTRACTOR_EXECUTABLE`. Le lanceur fourni par le
projet utilise Docker, mais un autre adaptateur respectant la même interface
pourrait lui être substitué.

`video_encoder` ne doit pas présumer :

- que CCExtractor est installé dans un emplacement système particulier ;
- que l’application qui demande l’export réside sur la même machine ;
- que les médias sont accessibles par le même chemin sur toutes les machines.

Lorsque `bin/video_encoder_ccextractor` est utilisé, Docker et l’image
CCExtractor configurée deviennent des dépendances explicites de cet adaptateur.

### Déploiement local par défaut

L’architecture exécutée sur une seule machine constitue le mode de
fonctionnement de référence tant qu’une distribution des services n’apporte
pas un bénéfice démontré.

Ce choix reste compatible avec l’utilisation d’un conteneur local et éphémère
pour CCExtractor : il ne crée ni worker distant ni transfert réseau des
médias.

Une évolution vers plusieurs machines devra répondre à un besoin concret, par exemple :

* rendre `vidb` disponible indépendamment du poste de traitement ;
* exécuter les exports en arrière-plan ;
* déplacer la médiathèque vers un serveur plus adapté ;
* mutualiser plusieurs workers ;
* remplacer le matériel actuel.

### Reproductibilité vérifiée

La reproductibilité ne repose pas uniquement sur une recette d’installation. Elle associe :

- une recette versionnée ;
- des versions ou artefacts identifiables ;
- les données linguistiques utilisées ;
- des empreintes de contrôle ;
- un test d’acceptation représentatif ;
- la conservation temporaire de la version précédemment validée.

Une mise à jour technique n’est considérée comme acceptable qu’après vérification du média final, notamment de la synchronisation et du contenu des sous-titres.

## Évolutions possibles

L’architecture permet plusieurs évolutions sans les imposer dès maintenant.

### Intégration avec `vidb`

`vidb` pourra devenir le point d’entrée permettant :

* de construire ou sélectionner un projet de montage ;
* de demander son export ;
* de suivre l’état du traitement ;
* de cataloguer le média produit.

La communication avec `video_encoder` pourra prendre la forme d’un appel local, d’une API, d’une table de travaux partagée ou d’une file de messages.

Ce choix sera effectué après l’assainissement de `vidb` et l’analyse précise de ses besoins.

### Worker distant

Un worker `video_encoder` pourra ultérieurement traiter des demandes provenant d’une autre machine.

Il devra alors recevoir une description versionnée du projet et accéder aux médias à l’aide de chemins ou d’identifiants stables.

### Serveur vidéo dédié

Une machine future pourra regrouper le stockage et les traitements audiovisuels si elle offre :

* une capacité de stockage suffisante ;
* une puissance de calcul adaptée ;
* une accélération matérielle compatible ;
* un réseau performant ;
* une stratégie de sauvegarde appropriée.

Ce serveur ne se confond pas nécessairement avec le poste de lecture installé près du téléviseur.

### Poste de lecture dédié

Le poste proche du téléviseur pourra fournir une interface silencieuse et peu énergivore pour consulter `vidb` et lire les médias.

Son choix technologique reste indépendant de l’architecture interne de `video_encoder`.

### Conteneurisation

La conteneurisation de CCExtractor est désormais retenue comme mode de
distribution de référence pour la chaîne OCR française.

Cette décision ne s’étend pas automatiquement aux autres composants.
`video_encoder`, FFmpeg, MLT et l’accès aux médias restent exécutés directement
sur le poste de traitement.

D’autres composants pourront être conteneurisés ultérieurement si leur
déplacement, leur isolation ou leur déploiement le justifie.

## Décisions différées

Les décisions suivantes sont volontairement reportées :

* l’hébergement définitif de `vidb` ;
* l’emplacement de sa base de données ;
* le protocole entre `vidb` et un worker distant ;
* l’utilisation éventuelle du Synology pour des services applicatifs ;
* le choix d’un futur serveur vidéo ;
* la technologie du poste de lecture,
* la conteneurisation éventuelle de composants autres que CCExtractor.

Ces décisions seront prises à partir de besoins observés et de tests sur les machines réellement ciblées.

Elles ne doivent pas complexifier le développement local actuel.