# Architecture de l’interface graphique

L’interface graphique de `video_encoder` est une application Python utilisant
PySide6 et les bindings MLT. Elle pilote le montage sans reprendre les règles
métier du moteur Ruby.

## Responsabilités

L’interface Python est responsable :

- de la sélection et de la prévisualisation des sources ;
- de la saisie des repères IN et OUT ;
- de la session d’édition en mémoire ;
- de l’affichage des segments conservés ;
- du lancement, du suivi et de l’annulation des processus externes ;
- de la présentation des avertissements et des résultats.

Le moteur Ruby reste responsable :

- du chargement et de la validation du projet persistant ;
- de l’analyse technique des médias ;
- de la sélection des pistes ;
- de la construction du projet MLT ;
- de l’extraction et de la composition des sous-titres ;
- du rendu vidéo et audio ;
- du remuxage final.

Cette séparation évite de dupliquer les règles de sélection et d’export dans
l’interface.

## Démarrage

L’application peut être lancée sans argument :

    bin/video_encoder_ui

Elle affiche alors une fenêtre d’accueil proposant trois parcours :

- créer un nouveau montage à partir d’une source vidéo ;
- ouvrir un projet de découpage JSON existant ;
- consulter et lancer la file des montages.

La consultation de la file ne nécessite pas l’ouverture préalable d’une source.
MLT n’est initialisé qu’au moment où un éditeur doit réellement être créé.

Un chemin peut également être fourni directement :

    bin/video_encoder_ui /chemin/source.m2t
    bin/video_encoder_ui /chemin/decoupage.json

Une vidéo ouvre une nouvelle session. Un fichier JSON restaure les sources et les segments enregistrés, 
puis positionne le moniteur sur le début du premier segment.

La fermeture de l’éditeur rend la main à la fenêtre d’accueil, sans terminer l’application.

L’éditeur ne prend actuellement en charge que les découpages mono-source. Le lecteur sait reconstruire 
les références de plusieurs sources, mais le démarrage de l’IHM refuse encore un tel projet.

## Document de découpage

Le format persistant canonique reste le document Ruby `video_encoder.trim_project`, actuellement en 
version 2. Les documents historiques en version 1 restent lisibles.

Lors de l’enregistrement, l’IHM transmet sa session au pont `TrimProjectBridge`.
Le moteur Ruby la valide, sonde les sources et produit le document persistant.

Lors de l’ouverture, `TrimProjectFileReader` lit directement ce document dans l’IHM.
Il valide le format et sa version, restaure les segments et déduplique les chemins des sources.

Les gaps présents dans un document sont actuellement refusés par l’éditeur, car la session Python 
ne sait pas encore les représenter.

Le JSON constitue une recette de montage transitoire. Il est utile pour :

- reprendre un montage non terminé ;
- préparer un export différé ;
- conserver un travail ayant échoué ;
- alimenter la file persistante des montages.

À terme, après un export réussi et la synchronisation des informations utiles
dans `vidb`, sa conservation ne sera pas obligatoire.

## Export

Avant l’export, l’IHM enregistre le découpage puis lance un contrôle audio.
Après confirmation de l’utilisateur, le JSON est archivé à côté du futur MKV.
L’utilisateur peut alors démarrer immédiatement l’export ou ajouter le montage à la file persistante.

Différer l’archivage jusqu’à cette confirmation évite de laisser un JSON orphelin dans le répertoire de 
destination lorsqu’un contrôle audio échoue ou que l’utilisateur abandonne l’opération.

Le contrôle audio mesure la présence d’un signal sur les pistes retenues. Les erreurs récupérables de 
paquets MPEG-TS n’interrompent pas le contrôle lorsque FFmpeg parvient malgré tout à analyser des 
échantillons.

L’IHM interprète les événements structurés émis par le moteur afin d’afficher :

- l’étape en cours ;
- la progression lorsqu’elle est mesurable ;
- les avertissements relatifs aux pistes ;
- le succès, l’échec ou l’annulation.

Le processus d’export est placé dans une nouvelle session Unix. Son annulation termine ainsi le groupe de 
processus, y compris les outils externes qu’il a lancés.

Lorsque `/usr/bin/systemd-inhibit` est disponible, l’export est exécuté sous une inhibition `sleep` en 
mode `block`. La suspension et l’hibernation du système sont empêchées pendant l’encodage, sans bloquer 
l’extinction ni le verrouillage de l’écran.

## File des montages

La file graphique utilise la même base SQLite et les mêmes travaux que la CLI Ruby. Elle permet :

- de consulter les montages préparés et leur état ;
- d’ajouter plusieurs projets sans les lancer immédiatement ;
- de démarrer ultérieurement leur exécution séquentielle ;
- d’actualiser automatiquement l’affichage pendant une exécution ;
- de conserver le nombre de tentatives et le diagnostic des échecs.

Les exports ne sont pas exécutés en parallèle. Un montage ajouté pendant l’exécution reste disponible 
pour un traitement ultérieur selon l’étendue du lancement en cours.

Lorsque la file est lancée depuis la fenêtre d’accueil, l’ouverture d’un éditeur et la fermeture de l’application 
sont désactivées jusqu’à la fin du processus.

## Évolutions prévues

Les prochaines évolutions de la file devront :

- afficher le diagnostic complet d’un travail en échec ;
- permettre sa relance explicite sans reprise automatique risquée ;
- distinguer clairement l’échec historique de la nouvelle tentative ;
- définir une politique contrôlée de validation puis de suppression des
  sources TV après export réussi.

Le montage multi-source viendra ensuite compléter l’éditeur avec plusieurs
sources, une couleur propre à chacune et des moniteurs adaptés, sans modifier
les responsabilités du moteur Ruby.
