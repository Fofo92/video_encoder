# Architecture du montage

## Objectif

Le sous-système de montage produit un média à partir d’une chronologie composée
de portions provenant d’une ou plusieurs sources.

Le domaine décrit le montage sans dépendre de FFmpeg, MLT, CCExtractor ni du
format de sortie. Des services applicatifs et des adaptateurs techniques
traduisent ensuite cette description en traitements exécutables.

## Modèle de domaine

### Segment

Un `Segment` représente une portion d’un média source.

Pour un projet persistant et un export à l’image près, il est défini par :

- une source `Media` ;
- une première image inclusive (`start_frame`) ;
- une dernière image inclusive (`end_frame`).

Le nombre d’images est donc :

```text
end_frame - start_frame + 1
```

`Segment` accepte encore des bornes temporelles pour certains usages
historiques, mais le format persistant exige des bornes en images afin d’éviter
toute perte de précision.

### Gap

Un `Gap` représente un intervalle volontaire dans la chronologie. Sa durée est
exprimée par un nombre strictement positif d’images.

Il permet notamment de matérialiser une portion manquante avant son éventuel
remplacement par un segment provenant d’une autre source.

### TrimProject

`TrimProject` contient une chronologie ordonnée de `Segment` et de `Gap`.

Un segment conserve toujours la référence à sa propre source. Le projet n’est
donc pas rattaché à un média unique.

Pour deux segments successifs provenant de la même source, le domaine refuse
les chevauchements et la contiguïté. Les segments provenant de sources
différentes restent indépendants dans leurs référentiels d’images respectifs.

`TrimProject` ne connaît ni les pistes à exporter, ni les outils de rendu, ni
le conteneur final.

## Persistance

### Format versionné

Un projet peut être sérialisé sous la forme d’un document JSON :

```json
{
  "format": "video_encoder.trim_project",
  "version": 1,
  "timeline": [
    {
      "type": "segment",
      "source": "/commun/video/source-a.m2t",
      "start_frame": 30000,
      "end_frame": 31499
    },
    {
      "type": "gap",
      "frame_count": 25
    }
  ]
}
```

`TrimProjectDocument` définit l’identité et la version du format.

`TrimProjectSerializer` transforme le domaine en JSON. Il refuse les segments
qui ne possèdent pas de bornes en images.

`TrimProjectLoader` valide le format et sa version, puis reconstruit le domaine.
Il utilise `MediaProbe` pour recalculer les informations techniques de chaque
source. Une source réutilisée dans plusieurs segments n’est sondée qu’une fois
pendant un chargement.

Le document ne duplique donc pas :

- la durée des médias ;
- leur cadence ;
- leurs pistes ;
- les résultats de la sélection des pistes.

Ces informations restent dérivées des fichiers source au moment de l’export.

## Services applicatifs

### ExportTrimProject

`ExportTrimProject` constitue le point d’entrée applicatif d’un projet déjà
chargé.

Il :

1. recueille les sources distinctes du projet ;
2. demande à `TrackSelector` les pistes vidéo, audio et de sous-titres ;
3. transmet le projet et ces sélections à `TrimExporter`.

### ExportTrimProjectFile

`ExportTrimProjectFile` adapte le cas d’utilisation précédent à un document
persistant.

Il :

1. lit le fichier JSON ;
2. le charge avec `TrimProjectLoader` ;
3. appelle `ExportTrimProject`.

Ce service forme la frontière commune entre la CLI actuelle et une future
interface Rails.

### Fabriques

`TrimExportFactory` assemble les composants nécessaires à l’export d’un
`TrimProject`.

`TrimProjectFileExportFactory` ajoute la lecture et le chargement d’un document
persistant.

Les dépendances techniques restent injectées afin de permettre leur
remplacement dans les tests ou dans une autre interface.

## Pipeline d’export

```text
Document JSON
    │
    ▼
TrimProjectLoader ──► MediaProbe
    │
    ▼
TrimProject
    │
    ▼
ExportTrimProject ──► TrackSelector
    │
    ▼
TrimExporter
    ├──► MltProjectBuilder
    ├──► MltRenderer
    ├──► TrimSubtitleExporter
    └──► FfmpegRemuxer
             │
             ▼
         média final
```

### Vidéo

`MltProjectBuilder` traduit la chronologie en projet MLT.

`MltRenderer` utilise `melt-7` pour produire une vidéo HEVC 1280 × 720,
progressive à 25 images par seconde.

### Audio

Les sorties audio sont construites par rôle fonctionnel, actuellement :

- français ;
- version originale.

Une piste n’est produite que si elle est disponible pour toutes les sources
concernées. Les pistes sont rendues séparément puis remultiplexées dans le
fichier final avec leurs métadonnées de langue.

### Sous-titres

La piste de sous-titres finale n’est produite que lorsqu’une sortie audio de
version originale complète est disponible pour toutes les sources du projet.

Les sous-titres DVB français standards sont convertis en SubRip afin de rester
sélectionnables sur les lecteurs qui ne prennent pas correctement en charge le
DVB dans Matroska.

Pour chaque groupe continu de segments admissibles :

1. `FfmpegSubtitleSegmentExtractor` produit un transport vidéo et DVB pour
   chaque segment ;
2. `FfmpegSubtitleProjectConcatenator` place ces transports sur la chronologie
   du projet ;
3. `CcextractorOcr` effectue une seule passe OCR sur le transport concaténé ;
4. `SrtNormalizer` retire les balises de présentation et borne les événements ;
5. `SrtComposer` rassemble et renumérote les résultats ;
6. `FfmpegRemuxer` ajoute la piste SubRip française au média final.

Le traitement OCR sur la chronologie concaténée évite les dérives d’horloge
observées lorsque chaque segment est interprété indépendamment.

## Interface en ligne de commande

La CLI expose l’export d’un projet persistant :

```bash
bin/video_encoder export projet.json --output montage.mkv
```

`VideoEncoder::CLI::ExportCommand` analyse les arguments, prépare le workspace
et construit le service avec `TrimProjectFileExportFactory`.

La CLI reste une interface : elle ne porte aucune règle métier du montage.

## Principes d’architecture

- Le domaine ne dépend d’aucun outil multimédia.
- Le document persistant contient les décisions de montage, pas les
  métadonnées dérivées.
- Les services applicatifs orchestrent les cas d’utilisation.
- Les adaptateurs encapsulent MLT, FFmpeg, FFprobe et CCExtractor.
- La CLI et la future IHM Rails doivent appeler les mêmes services.
- Les traitements longs devront être exécutés hors du cycle d’une requête HTTP.
