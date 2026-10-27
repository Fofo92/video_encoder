# Architecture de l’interface graphique

État actuel : [montage manuel et file d’encodage](../manual-editing.md). Les anciens parcours de détection ne sont plus intégrés à l’éditeur.

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

Elle affiche directement la file des montages et ses onglets. Les menus Sources,
Projets et Montage donnent accès à l’ouverture d’une capture, à la quarantaine,
à l’ouverture et au déplacement d’un projet, à la création d’un montage et aux
commandes de la file. Il n’y a plus de fenêtre de choix ni de bouton pour afficher
une file qui constitue déjà l’accueil.

La file reste visible pendant l’édition. MLT n’est initialisé que lorsqu’un éditeur
est créé. Les fenêtres s’ouvrent dans le tiers gauche et la moitié supérieure de
la zone disponible de l’écran courant ; leurs minima restent prioritaires sur les
très petits écrans. La liste des segments réserve sa place dès l’ouverture.

Un chemin peut également être fourni directement :

    bin/video_encoder_ui /chemin/source.m2t
    bin/video_encoder_ui /chemin/decoupage.json

Une vidéo ouvre une nouvelle session. Un fichier JSON restaure les sources et les segments enregistrés, 
puis positionne le moniteur sur le début du premier segment.

La fermeture de l’éditeur rend la main à la fenêtre d’accueil, sans terminer l’application.

L’éditeur permet aussi de monter plusieurs sources dans un projet, sous réserve
qu’elles aient la même cadence. Le sélecteur de source, les segments et leur ordre
sont décrits dans [Montage multi-source](multi-source-editor.md).

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

Avant l’export, l’IHM propose l’identification vidb et la destination, enregistre
le projet JSON à côté du futur MKV, puis lance un contrôle audio. L’utilisateur
confirme ensuite l’export immédiat ou la mise en file. Annuler le contrôle conserve
le projet enregistré et ne lance aucune tâche. Voir
[Identifier puis mettre en file](identify-then-queue.md).

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
- d’arrêter la file après la réussite du montage en cours ;
- d’interrompre explicitement le montage en cours sans lancer les suivants ;
- d’actualiser automatiquement l’affichage pendant une exécution ;
- de conserver le nombre de tentatives et le diagnostic des échecs ou interruptions ;
- de créer une nouvelle tentative depuis un travail échoué ou interrompu.

Les exports ne sont pas exécutés en parallèle. Un montage ajouté pendant l’exécution reste disponible 
pour un traitement ultérieur selon l’étendue du lancement en cours.

La file s’exécute dans une session Unix dédiée. Une interruption confirmée envoie `SIGINT` à tout le
groupe de processus afin d’arrêter également FFmpeg, MLT, Docker et CCExtractor. Le travail courant
prend alors le statut `interrupted`, tandis que les autres travaux conservent le statut `queued`.

L’arrêt après le montage courant utilise au contraire un marqueur temporaire transmis au worker. Le
processus courant termine normalement et prend le statut `done`. Le worker consulte ensuite le marqueur
avant de réclamer un autre travail, puis quitte en laissant les travaux suivants au statut `queued`.

Chaque travail en cours mémorise le PID de son worker. Au démarrage suivant, un travail resté `running`
dont le PID n’existe plus est reclassé `interrupted` avec un diagnostic d’arrêt inattendu. Un PID encore
actif empêche le lancement d’un second worker.

La relance depuis l’interface crée un nouveau travail. Le travail interrompu ou échoué reste dans
l’historique avec son diagnostic et son nombre de tentatives.

La fermeture de l’accueil est refusée pendant le traitement de la file. Un éditeur
peut être ouvert pendant ce traitement ; sa fermeture ne doit pas interrompre le
worker partagé. Le déplacement d’un projet et la quarantaine sont indisponibles
tant qu’un éditeur est ouvert, pour éviter de déplacer un document encore utilisé.

## Évolutions prévues

Les prochaines évolutions de la file devront :

- ajouter un verrou exclusif atomique avant qu’un orchestrateur externe tel que `vidb` puisse lancer
  plusieurs workers simultanément ;
- définir une politique de durée et de suppression des fichiers en quarantaine.

La fin d’utilisation d’une source demande déjà une confirmation explicite avant
sa mise en quarantaine : [protocole](source-completion-confirmation.md).

## Navigation et déplacement des projets

Le menu Montage de l’éditeur propose Nouveau montage, Encoder le montage et
Ajouter le montage à la file. Les commandes image précédente/suivante restent
accessibles au clavier et à la souris, sans boutons supplémentaires. Les anciens
boutons Navigation et −1/+1 sont retirés de l’affichage ; les ajustements IN/OUT
restent accessibles depuis Montage et Ctrl+←/→.

La couronne du ShuttleXpress conserve ses vitesses d’origine, de 1× à 50× dans les deux sens.
L’accélération de la molette verticale est limitée à 1, 2 ou 3 images par cran.

Le déplacement est décrit dans [project-relocation.md](project-relocation.md).
