# Pipeline d’export

## Objectif

`video_encoder` charge un projet de montage persistant, sélectionne les pistes
communes à ses sources et produit un fichier Matroska. Le même service
applicatif est utilisé par la CLI et par l’interface graphique, directement ou
au travers de la file persistante.

## Entrées

Un export peut être lancé :

- immédiatement avec la commande `export` ;
- depuis l’interface graphique ;
- après ajout à la file avec `enqueue-trim-export`.

Le document JSON conserve les chemins des sources, l’ordre de la chronologie,
les bornes inclusives des segments et les éventuels gaps.

## File persistante

`JobRepository` enregistre des `TrimExportJob` dans SQLite.
`TrimExportWorker` réclame le prochain travail en attente, marque son
propriétaire et exécute les exports séquentiellement.

Les états `queued`, `running`, `done`, `failed` et `interrupted`
permettent à l’interface de restituer le cycle de vie du travail. Un processus
arrêté sans avoir finalisé son travail est détecté au lancement suivant et son
export est reclassé `interrupted`.

## Vue d’ensemble

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

## Chargement et sélection

`TrimProjectLoader` valide le format, sonde les sources et reconstruit le
`TrimProject`.

`ExportTrimProject` recueille ensuite les sources distinctes puis demande à
`TrackSelector` :

- une piste vidéo par source ;
- les sorties audio disponibles pour toutes les sources ;
- une piste de sous-titres français standards par source lorsqu’elle existe.

## Rendu

`TrimExporter` orchestre les adaptateurs techniques :

- `MltProjectBuilder` construit les projets MLT ;
- `MltRenderer` produit séparément la vidéo et les pistes audio ;
- `TrimSubtitleExporter` produit une piste SubRip française ;
- `FfmpegRemuxer` assemble les flux dans le conteneur final.

Le workspace temporaire est isolé à côté du fichier de sortie. Il est supprimé
après un export réussi et conservé pour diagnostic en cas d’échec.

L’architecture détaillée est décrite dans `trim.md`.

## Composants partagés

`MediaProbe` transforme les données FFprobe en objets `Media` et `Track`.
Il décrit les médias sans décider quelles pistes conserver.

`TrackSelector` porte les règles de sélection indépendamment de FFmpeg, MLT
et de l’interface appelante.

`CommandRunner` exécute des commandes sous forme de tableaux d’arguments,
sans passer par un shell. Les adaptateurs spécialisés construisent leurs
commandes ; le runner se limite à leur exécution.

## Principes

- Un objet métier ne construit pas de commande externe.
- Les règles de sélection restent séparées des adaptateurs multimédias.
- La CLI, l’interface graphique et le worker utilisent les mêmes services
  applicatifs.
- Les fichiers temporaires sont isolés dans des workspaces dédiés.
