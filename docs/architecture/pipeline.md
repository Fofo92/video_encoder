# Pipelines de traitement

## Objectif

`video_encoder` fournit deux pipelines complémentaires :

- l’encodage automatique d’un média placé dans une file de travaux ;
- l’export d’un projet de montage persistant et potentiellement multi-source.

Ils partagent certains composants, notamment `MediaProbe`, `TrackSelector` et
les adaptateurs FFmpeg, mais répondent à deux cas d’utilisation distincts.

## Encodage automatique

### Vue d’ensemble

```text
Média entrant
    │
    ▼
Watcher / CLI
    │
    ▼
JobRepository
    │
    ▼
Worker
    ├──► MediaProbe
    ├──► TrackSelector
    ├──► Encoder
    ├──► Verifier
    └──► Workspace
             │
             ▼
         média encodé
```

### Entrée dans la file

`Watcher` détecte les médias du répertoire d’entrée. La commande `enqueue`
permet également d’ajouter explicitement un fichier.

Le travail est persisté dans `JobRepository`, actuellement adossé à SQLite.

### Worker

`Worker` récupère un travail disponible et coordonne son traitement.

Il ne contient pas les règles de sélection des pistes ni la construction des
commandes FFmpeg.

### Analyse et sélection

`MediaProbe` décrit fidèlement le conteneur et toutes ses pistes à partir de
FFprobe.

`TrackSelector` applique ensuite les règles métier de sélection. Ces règles
sont décrites dans `track_selection.md`.

### Encodage

L’encodeur configuré produit le média cible. Le profil fourni utilise FFmpeg,
HEVC NVENC, un redimensionnement maximal en 1280 × 720, un désentrelacement et
un audio AAC.

### Vérification et finalisation

`Verifier` contrôle le média produit.

`Workspace` gère les déplacements entre les répertoires de travail,
l’archivage de la source et la mise à disposition du résultat final.

## Export d’un projet de montage

### Vue d’ensemble

```text
Document JSON
    │
    ▼
ExportTrimProjectFile
    ├──► TrimProjectLoader ──► MediaProbe
    │
    ▼
ExportTrimProject
    ├──► TrackSelector
    │
    ▼
TrimExporter
    ├──► rendu vidéo MLT
    ├──► rendus audio MLT
    ├──► conversion OCR des sous-titres DVB
    └──► remultiplexage FFmpeg
             │
             ▼
         média monté
```

### Chargement

Le document JSON conserve uniquement les décisions de montage :

- ordre de la chronologie ;
- chemins des sources ;
- bornes inclusives en images ;
- éventuels gaps.

`TrimProjectLoader` valide le format, sonde les sources et reconstruit le
`TrimProject`.

### Sélection multi-source

`ExportTrimProject` recueille les sources distinctes puis demande à
`TrackSelector` :

- une piste vidéo par source ;
- les sorties audio disponibles pour toutes les sources ;
- une piste de sous-titres français standards par source lorsqu’elle existe.

### Rendu

`TrimExporter` orchestre les adaptateurs techniques :

- `MltProjectBuilder` construit les projets MLT ;
- `MltRenderer` produit séparément la vidéo et les pistes audio ;
- `TrimSubtitleExporter` produit une piste SubRip française ;
- `FfmpegRemuxer` assemble les flux dans le conteneur final.

L’architecture détaillée est décrite dans `trim.md`.

### Interface

La CLI fournit actuellement l’entrée générique :

```bash
bin/video_encoder export projet.json --output montage.mkv
```

Une future IHM doit appeler les mêmes services applicatifs dans un worker
asynchrone, sans exécuter les outils multimédias pendant une requête HTTP.

## Composants partagés

### MediaProbe

`MediaProbe` transforme les données FFprobe en objets `Media` et `Track`.

Il décrit les médias, mais ne décide jamais quelles pistes doivent être
conservées.

### TrackSelector

`TrackSelector` porte les règles de sélection, indépendamment de FFmpeg, MLT et
de l’interface appelante.

### CommandRunner

`CommandRunner` exécute des commandes sous forme de tableaux d’arguments, sans
passer par un shell.

Les adaptateurs spécialisés construisent leurs commandes ; le runner se limite
à leur exécution.

## Principes

- Un objet métier ne construit pas de commande externe.
- Les règles de sélection restent séparées des adaptateurs multimédias.
- Les pipelines automatiques et de montage partagent des composants sans être
  confondus.
- La CLI, un worker et une future IHM utilisent les mêmes services
  applicatifs.
- Les fichiers temporaires sont isolés dans des workspaces dédiés.
