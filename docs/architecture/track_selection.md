# Sélection des pistes

## Objectif

`TrackSelector` centralise les règles métier déterminant quelles pistes d’un
média doivent être conservées.

Il travaille exclusivement sur les objets produits par `MediaProbe`. Il ne
construit aucune commande FFmpeg ou MLT et ne dépend pas de l’interface qui
déclenche l’encodage ou le montage.

## Codes de langue reconnus

Les codes actuellement reconnus sont :

| Rôle              | Codes        |
| ----------------- | ------------ |
| Français          | `fra`, `fre` |
| Version originale | `qaa`        |

Une autre langue étrangère n’est pas utilisée comme substitut implicite de la
version originale.

## Sélection pour un média unique

La méthode `select(media)` retourne :

- la première piste vidéo ;
- la première piste audio française utilisable ;
- la première piste audio de version originale utilisable ;
- les sous-titres français standards admissibles.

### Vidéo

La première piste vidéo décrite par le conteneur est sélectionnée.

### Audio

Les pistes marquées comme destinées aux personnes déficientes visuelles sont
exclues.

Parmi les pistes restantes, le sélecteur conserve au plus :

1. la première piste française ;
2. la première piste portant le code de version originale `qaa`.

La collection finale est dédupliquée. Une piste étrangère portant un autre
code, par exemple `deu`, ne remplace pas une piste `qaa` absente.

### Sous-titres

Les sous-titres ne sont sélectionnés que lorsqu’une piste audio de version
originale est elle-même conservée.

Parmi les sous-titres disponibles, sont retenues les pistes :

- de langue française (`fra` ou `fre`) ;
- non marquées comme destinées aux personnes malentendantes.

Cette règle évite d’ajouter des sous-titres français à un média ne contenant
qu’un doublage français, tout en accompagnant une véritable version originale.

## Sélection multi-source

L’export d’un `TrimProject` demande des sélections adaptées à plusieurs
sources.

### Vidéo par source

`select_video_tracks(media_sources)` associe chaque source à sa première piste
vidéo.

Le résultat conserve l’identité de la source afin que le constructeur MLT
puisse utiliser la bonne piste pour chaque segment.

### Sorties audio complètes

`select_audio_outputs(media_sources)` construit des `AudioOutputTrack` par
rôle :

- `french` ;
- `original`.

Une sortie n’est créée que si une piste du rôle correspondant est disponible
dans toutes les sources du projet.

Cette contrainte garantit qu’une piste audio finale reste continue sur toute
la chronologie. Par exemple, si une source ne contient aucune piste `qaa`, la
sortie originale complète est omise.

Les pistes d’accessibilité visuelle restent exclues avant cette vérification.

### Sous-titres par source

`select_subtitle_tracks(media_sources)` sélectionne au plus une piste de
sous-titres par source admissible.

La sélection des sous-titres exige d’abord qu’une sortie audio originale
complète puisse être construite. Si une source ne possède aucune piste `qaa`,
la sélection retourne un ensemble vide pour tout le projet.

Lorsque la sortie originale est complète, les sous-titres ne doivent en
revanche pas être présents dans toutes les sources. Les segments sans
sous-titres interrompent simplement le groupe traité par
`TrimSubtitleExporter`.

## Responsabilités

`TrackSelector` décide :

- quels rôles fonctionnels sont admissibles ;
- quelles pistes représentent ces rôles ;
- si une sortie multi-source peut être continue.

Les adaptateurs techniques décident ensuite :

- comment lire les pistes ;
- comment les rendre ;
- comment les convertir ;
- comment les remultiplexer et écrire leurs métadonnées.

Cette séparation permet de tester les règles de sélection sans exécuter
FFmpeg, MLT ou CCExtractor.