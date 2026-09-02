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

```bash
bin/video_encoder_ui
```

Elle demande alors de sélectionner une vidéo ou un fichier JSON de découpage.

Elle accepte également directement l’un de ces chemins :

```bash
bin/video_encoder_ui /chemin/source.m2t
bin/video_encoder_ui /chemin/decoupage.json
```

Une vidéo ouvre une nouvelle session. Un fichier JSON restaure les sources et les segments enregistrés,
puis positionne le moniteur sur le début du premiersegment.

L’éditeur ne prend actuellement en charge que les découpages mono-source. Le lecteur sait reconstruire
les références de plusieurs sources, mais le démarrage de l’IHM refuse encore un tel projet.

## Document de découpage

Le format persistant canonique reste le document Ruby `video_encoder.trim_project`,
actuellement en version 1.

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
- alimenter la future file d’attente.

À terme, après un export réussi et la synchronisation des informations utiles
dans `vidb`, sa conservation ne sera pas obligatoire.

## Export

Avant l’export, l’IHM enregistre le découpage puis lance un contrôle audio. La confirmation de l’utilisateur
déclenche ensuite la commande Ruby `export` dans un `QProcess` séparé.

L’IHM interprète les événements structurés émis par le moteur afin d’afficher :

- l’étape en cours ;
- la progression lorsqu’elle est mesurable ;
- les avertissements relatifs aux pistes ;
- le succès, l’échec ou l’annulation.

Le processus d’export est placé dans une nouvelle session Unix. Son annulation termine ainsi le groupe de
processus, y compris les outils externes qu’il a lancés.

Lorsque `/usr/bin/systemd-inhibit` est disponible, l’export est exécuté sousune inhibition `sleep` en mode `block`. La suspension et l’hibernation du système sont donc empêchées pendant l’encodage, sans
bloquer l’extinction ni le verrouillage de l’écran.

## Évolutions prévues

La file d’attente graphique sera implémentée dans un composant distinct de la
fenêtre principale. Elle devra :

- conserver plusieurs travaux préparés ;
- exécuter les exports successivement, sans parallélisme ;
- persister leur état ;
- permettre la reprise après le redémarrage de l’application ;
- conserver les diagnostics des échecs ;
- supprimer les recettes transitoires devenues inutiles selon la politique
  retenue.

Le montage multi-source viendra ensuite compléter l’éditeur avec plusieurs
sources et des moniteurs adaptés, sans modifier le format persistant du moteur.
