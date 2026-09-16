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

`ExportTrimProject` constitue le point d’entrée applicatif d’un projet déjà chargé. Il :

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

Ce service charge les projets persistants pour l’export CLI. L’IHM Python/Qt lance cette CLI dans un processus asynchrone.

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

Chaque segment possède sa propre chaîne MLT, même lorsque plusieurs segments
réutilisent le même média source. La source reste unique dans le modèle de
domaine ; seule son instance de traitement MLT est distincte.

Cette isolation corrige un défaut reproduit sur un enregistrement DVB :
avec une chaîne partagée, une image publicitaire apparaissait au début d’un
segment malgré un point IN correct dans la prévisualisation. Le défaut
disparaissait avec des chaînes distinctes, puis cette correction a été
confirmée sur le rendu complet.

Le mécanisme interne exact du défaut n’est pas établi. Aucune compensation
systématique de plus ou moins une image n’est appliquée aux bornes.

Les bornes IN et OUT restent inclusives. Lorsque les cadences source et sortie
diffèrent, le début est converti par arrondi inférieur, et la fin exclusive par
arrondi supérieur avant conversion en fin inclusive.

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

1. `TrimExporter` rend d’abord la vidéo finale avec MLT ;
2. `FfmpegSubtitleSegmentExtractor` produit un transport vidéo et DVB pour chaque segment ;
3. `SubtitleSegmentSynchronizationProbe` mesure la position temporelle du segment dans la vidéo
   finale et dans son transport intermédiaire ;
4. `FfmpegSubtitleProjectConcatenator` place les transports sur la chronologie du projet ;
5. `CcextractorOcr` effectue une seule passe OCR sur le transport concaténé ;
6. `SubtitleTimelineNormalizer` applique la correction propre à chaque segment, borne les événements
   et délègue leur nettoyage à `SrtNormalizer` ;
7. `SrtComposer` rassemble et renumérote les résultats ;
8. `FfmpegRemuxer` ajoute la piste SubRip française au média final.

### Synchronisation par segment

La synchronisation n’est pas déduite des seuls horodatages déclarés par les conteneurs. Certains
enregistrements DVB et certains rendus MLT présentent un décalage effectif qui dépend de la source et de
son décodage.

Pour chaque segment, `VideoTimelineOffsetProbe` compare des séquences d’images normalisées :

- entre la source et la vidéo finale rendue ;
- entre la source et le transport intermédiaire destiné à l’OCR.

La correction des sous-titres est la différence entre ces deux alignements.
Elle est donc propre au segment et ne constitue pas une compensation globale appliquée arbitrairement à
tous les médias.

Les comparaisons utilisent des images en niveaux de gris de 32 × 18 pixels à 25 images par seconde, sur un
échantillon de douze secondes. Une prélecture de cinq secondes fiabilise le décodage des sources H.264.

Une mesure n’est acceptée que si les deux corrélations atteignent une confiance minimale de 0,95. Lorsque
le début d’un segment est visuellement peu discriminant, le système essaie successivement les positions 0,
15, 30, 60 et 120 secondes, sans dépasser la durée disponible. Il s’arrête dès la première mesure
suffisamment fiable. Si aucune position ne convient, l’export échoue au lieu d’appliquer une correction
incertaine.

`SubtitleTimelineNormalizer` applique ensuite chaque correction uniquement aux événements OCR
appartenant à l’intervalle du segment correspondant. Cette restriction empêche un événement situé près
d’une coupure de déborder dans le segment voisin.

### Validation réelle

Le mécanisme a été validé sur un montage DVB réel composé de trois segments.
Les premier et troisième segments ont été corrélés dès leur début avec une confiance proche de 1. Le
début du deuxième segment était ambigu (`0,837`) ; la mesure effectuée quinze secondes plus tard a
atteint `1,000`.

La correction obtenue était stable, de l’ordre de `−1,96 s` pour les trois segments. L’export complet a été
contrôlé visuellement avant, entre et après les coupures : vidéo, audio et sous-titres étaient synchrones. Le
workspace a ensuite été supprimé normalement.

## Erreurs et conservation des résultats

`CommandRunner::CommandFailed` expose séparément le code de sortie et le
signal éventuel du processus.

`CcextractorOcr` traduit le code de sortie 10, sans signal de terminaison,
en `NoSubtitlesFound`. Les autres échecs restent des erreurs techniques.

Lorsqu’un groupe ne fournit aucun sous-titre, `TrimSubtitleExporter` poursuit
l’examen des autres groupes. Il compose et conserve les résultats valides,
sans déplacer leurs positions temporelles, puis lève `IncompleteSubtitles`.
Cette erreur indique les groupes manquants et le chemin du SRT partiel,
s’il existe.

`TrimExporter` signale les groupes manquants au rapporteur d’avertissements
lorsqu’il est disponible, puis propage l’erreur. Le remuxage n’est pas lancé.

L’IHM Qt reçoit les avertissements sur un signal distinct de la progression.
Elle les conserve dans une zone permanente de la barre d’état. Leur affichage
ne constitue pas une autorisation de poursuivre.

`WorkspaceCleaningExporter` nettoie le workspace après le retour normal de
l’exporteur. Une exception empêche ce nettoyage. La validation automatique
du média final avant nettoyage reste à renforcer.

Le remuxage utilise `-nostdin` et `-n` : il n’attend pas de réponse interactive
et refuse d’écraser une sortie existante.

La reprise depuis un workspace, la confirmation de poursuite sans certains
sous-titres et la réutilisation automatique des composants validés ne sont
pas encore implémentées.## Interface en ligne de commande

La CLI expose l’export d’un projet persistant :

```bash
bin/video_encoder export projet.json --output montage.mkv
```

`VideoEncoder::CLI::ExportCommand` analyse les arguments, prépare le workspace
et construit le service avec `TrimProjectFileExportFactory`.

La CLI reste une interface : elle ne porte aucune règle métier du montage.

## Principes d’architecture

- Le domaine ne dépend d’aucun outil multimédia.
- Le document persistant contient les décisions de montage, pas les métadonnées dérivées.
- Les services applicatifs orchestrent les cas d’utilisation.
- Les adaptateurs encapsulent MLT, FFmpeg, FFprobe et CCExtractor.
- La CLI et l’IHM Python/Qt utilisent le même moteur Ruby d’export.
- L’IHM exécute l’export dans un processus distinct pour rester réactive.
