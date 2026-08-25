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

### Installation locale

À court terme, CCExtractor avec OCR français sera installé localement sur le poste Debian dans un emplacement propre à `video_encoder`. L’installation devra être :

* versionnée ;
* indépendante d’un remplacement implicite dans `/usr/local/bin` ;
* accompagnée de sa recette de construction ;
* accompagnée de la liste de ses dépendances ;
* associée au modèle linguistique français validé ;
* vérifiée par un test d’acceptation représentatif.



Une organisation possible est :

```text
/opt/video_encoder/ccextractor/
├── 0.96.5/
└── 0.96.6/
```



Chaque version devra pouvoir être sélectionnée explicitement avec la variable d’environnement `CCEXTRACTOR_EXECUTABLE` :

```shell
CCEXTRACTOR_EXECUTABLE=\
/opt/video_encoder/ccextractor/0.96.6/bin/ccextractor \
  bin/video_encoder export projet.json --output montage.mkv
```



Une mise à jour ne devra pas écraser immédiatement la version précédemment validée.

La nouvelle version sera d’abord considérée comme candidate, puis comparée à la version de référence
au moyen du projet d’acceptation multi-source.

La documentation de l’installation devra au minimum préciser :

- la version ou le commit de CCExtractor ;

- la version de Tesseract ;
- les options de compilation ;
- les paquets Debian nécessaires ;
- l’origine et l’emplacement de fra.traineddata ;
- les éventuelles variables d’environnement ;
- les empreintes des principaux artefacts ;
- les commandes de vérification et d’acceptation.

### Image de référence

L’image conteneurisée déjà validée est conservée comme environnement de référence et
comme solution de secours.

Elle ne constitue pas une dépendance obligatoire pour l’exécution courante de video_encoder.

Elle pourra notamment servir à :

- reproduire l’environnement OCR validé ;

- comparer le résultat d’une installation locale candidate ;
- diagnostiquer une régression après une mise à jour ;
- préparer un éventuel déploiement sur une autre machine ;
- revenir temporairement à une chaîne connue.

La conservation de l’image ne dispense pas de documenter :

- son image de base ;

- les versions des logiciels intégrés ;
- les fichiers linguistiques utilisés ;
- sa recette de construction ;
- son empreinte immuable ;
- le test d’acceptation associé.

Le résultat attendu de l’installation locale et celui de l’image de référence doivent être fonctionnellement équivalents.

Les différences éventuelles devront être examinées avant qu’une nouvelle version ne remplace la référence.

## Principes de conception

L’architecture de déploiement respecte les principes suivants.

### Traitements au plus près des médias

Les opérations qui lisent ou produisent des fichiers volumineux sont exécutées sur la machine qui héberge la médiathèque.

Cette proximité limite les transferts réseau et évite de rendre le pipeline dépendant de la disponibilité d’un stockage distant.

### Séparation entre pilotage et exécution

La construction d’un projet, la demande d’un export et l’exécution du traitement constituent des responsabilités distinctes.

À terme, `vidb` pourra demander un export sans devoir exécuter directement FFmpeg, MLT ou CCExtractor.  Le worker de `video_encoder` restera responsable des traitements audiovisuels.

### Dépendances explicites

Les chemins des exécutables externes et les paramètres propres à l’environnement doivent rester configurables. `video_encoder` ne doit pas présumer :

* que CCExtractor est installé dans un emplacement système particulier ;
* que l’application qui demande l’export réside sur la même machine ;
* que les médias sont accessibles par le même chemin sur toutes les machines ;
* qu’un moteur de conteneurs est disponible.

### Déploiement local par défaut

L’architecture locale constitue le mode de fonctionnement de référence tant qu’une distribution des services n’apporte pas un bénéfice démontré.

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

Les composants pourront être conteneurisés si leur déplacement ou leur isolement le justifie. La conteneurisation demeure un moyen de distribution possible et non un principe imposé à toute l’architecture.

## Décisions différées

Les décisions suivantes sont volontairement reportées :

* l’hébergement définitif de `vidb` ;
* l’emplacement de sa base de données ;
* le protocole entre `vidb` et un worker distant ;
* l’utilisation éventuelle du Synology pour des services applicatifs ;
* le choix d’un futur serveur vidéo ;
* la technologie du poste de lecture ;
* le format définitif de distribution de CCExtractor ;
* la conteneurisation éventuelle des différents composants.

Ces décisions seront prises à partir de besoins observés et de tests sur les machines réellement ciblées.

Elles ne doivent pas complexifier le développement local actuel.