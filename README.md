# Video Encoder

Pipeline Ruby d’encodage et de montage vidéo, conçu principalement pour des
enregistrements TNT.

Le projet comporte actuellement deux chaînes complémentaires :

- une file de travaux pour automatiser l’encodage, la vérification et
  l’archivage des médias ;
- un domaine de montage non destructif capable d’assembler des segments issus
  de plusieurs sources.

## Fonctionnalités

### Encodage automatique

- surveillance d’un répertoire d’entrée ;
- mise en file des médias dans SQLite ;
- encodage avec FFmpeg ;
- sélection automatique des pistes vidéo, audio et de sous-titres ;
- vérification du fichier produit ;
- archivage de la source ;
- suivi des travaux terminés ou en échec.

Le profil fourni produit un fichier Matroska HEVC en 1280 × 720, avec
désentrelacement et audio AAC. Il utilise `hevc_nvenc` par défaut et nécessite
donc un FFmpeg compatible NVIDIA NVENC.

### Montage multi-source

Le domaine de montage permet :

- de sélectionner des segments à l’image près ;
- d’assembler des segments provenant de plusieurs médias ;
- de convertir les repères temporels selon la cadence propre à chaque source ;
- de produire une vidéo HEVC 720p25 progressive avec MLT ;
- de conserver, lorsqu’elles sont disponibles dans toutes les sources, une
  piste française et une piste en version originale ;
- de convertir les sous-titres DVB français en SubRip avec CCExtractor et
  Tesseract ;
- de composer une piste de sous-titres unique sur la chronologie du montage ;
- de supprimer les balises de présentation issues de l’OCR et de borner les
  sous-titres aux plages exportées.

Les segments consécutifs possédant des sous-titres sont d’abord concaténés sur
la chronologie du projet. CCExtractor effectue ensuite une seule passe OCR sur
cet ensemble, ce qui évite les dérives d’horloge observées lors d’un traitement
indépendant de chaque segment.

Cette chaîne est exposée par le service `ExportTrimProject` construit par
`TrimExportFactory`. Elle pourra ainsi être utilisée par une future interface
graphique sans dépendre des scripts expérimentaux.

## Prérequis

- Ruby 3.3 ou version ultérieure ;
- Bundler ;
- FFmpeg et FFprobe ;
- SQLite 3 ;
- `melt-7` pour les exports de montage ;
- une prise en charge NVENC pour le profil d’encodage fourni.

La conversion facultative des sous-titres DVB nécessite également Docker.
Le projet fournit une image dédiée contenant :

- CCExtractor avec prise en charge OCR ;
- Tesseract ;
- les données linguistiques françaises de Tesseract.

Seul CCExtractor est exécuté dans ce conteneur. FFmpeg, FFprobe, MLT et
`video_encoder` restent exécutés directement sur la machine hôte.

La construction et les possibilités de déploiement futur sont décrites dans
la [documentation d’architecture](docs/architecture/deployment.md).

## Installation

```bash
git clone https://github.com/Fofo92/video_encoder.git
cd video_encoder
bundle install
```

Pour activer la conversion des sous-titres DVB, construis l’image CCExtractor
validée :

```bash
bin/build_ccextractor_image 0.96.6
```

Cette commande produit l’image locale :

```text
video-encoder-ccextractor:0.96.6-ocr-fra
```

## Utilisation de la CLI

Depuis le dépôt :

```bash
bin/video_encoder version
bin/video_encoder config
bin/video_encoder enqueue /chemin/vers/un-media.m2t
bin/video_encoder list
bin/video_encoder status IDENTIFIANT
bin/video_encoder failed
bin/video_encoder run --once
bin/video_encoder run
bin/video_encoder watch --once
bin/video_encoder watch
```

`run --once` traite un seul travail disponible. Sans `--once`, le worker
continue à traiter la file jusqu’à son interruption.

`watch --once` effectue un seul balayage du répertoire d’entrée. Sans
`--once`, la surveillance reste active.

### Exporter un projet de montage

La commande `export` charge un projet persistant, sonde ses sources avec
FFprobe, sélectionne les pistes disponibles puis exécute l’export complet.

Pour utiliser l’image CCExtractor fournie par le projet :

```bash
CCEXTRACTOR_EXECUTABLE="$PWD/bin/video_encoder_ccextractor" \
  bin/video_encoder export projet.json --output montage.mkv
```

Le workspace est créé à côté du fichier de sortie. Pour un fichier
`montage.mkv`, son nom est `video_encoder_montage_workspace`. Il est supprimé
après un export réussi et conservé lorsqu’une erreur interrompt le traitement.

Le lanceur CCExtractor démarre un conteneur éphémère sans accès réseau, monte
uniquement le workspace nécessaire et le supprime à la fin du traitement.

Pour comparer les résultats avec la version précédente ou effectuer un retour
arrière, construis d’abord cette version :

```bash
bin/build_ccextractor_image 0.96.5
```

puis sélectionne son image explicitement :

```bash
VIDEO_ENCODER_CCEXTRACTOR_IMAGE=\
video-encoder-ccextractor:0.96.5-ocr-fra \
CCEXTRACTOR_EXECUTABLE="$PWD/bin/video_encoder_ccextractor" \
  bin/video_encoder export projet.json --output montage.mkv
```

Un autre exécutable compatible peut également être fourni directement avec
`CCEXTRACTOR_EXECUTABLE`.

Avant de démarrer un traitement, la CLI vérifie les dépendances externes
nécessaires à la commande :

- `run` vérifie la présence de `ffmpeg` et `ffprobe` lorsque l’encodeur FFmpeg
  est configuré ;
- `export` vérifie `ffmpeg`, `ffprobe`, `melt-7` et l’exécutable CCExtractor
  configuré.

Si une dépendance manque, la commande s’arrête avec un code de sortie non nul
avant de créer le workspace ou de lancer un traitement externe. Les commandes
qui n’utilisent pas ces outils, telles que `version`, restent disponibles.

Le format persistant est un document JSON versionné :

```json
{
  "format": "video_encoder.trim_project",
  "version": 1,
  "timeline": [
    {
      "type": "segment",
      "source": "/commun/video/source.m2t",
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

Les bornes `start_frame` et `end_frame` sont inclusives. Les métadonnées
techniques du média — durée, cadence et pistes — ne sont pas dupliquées dans
le document : elles sont recalculées depuis chaque source lors du chargement.
Une même source réutilisée dans plusieurs segments n’est sondée qu’une fois.

## Contrôle qualité

Le contrôle standard vérifie les dépendances Ruby, la syntaxe des scripts
shell, RuboCop et les tests unitaires :

```bash
bin/check
```

Pour ajouter les tests d’intégration MLT :

```bash
bin/check --integration
```

ou :

```bash
bin/check --all
```

Les tests d’intégration sont ignorés automatiquement lorsque `melt-7` n’est
pas disponible.

## Outils de développement

`bin/generate_mlt.rb` et `bin/export_multi_source_test.rb` sont des scénarios
techniques utilisés pendant le développement et les essais d’acceptation. Ils
contiennent des sources et des plages de montage propres à l’environnement de
développement ; ils ne constituent pas encore une interface utilisateur
générique.

## État du projet

Version actuelle : **0.2.0**

Le pipeline d’encodage dispose d’une CLI. Le domaine de montage multi-source
et son export sont fonctionnels, mais leur intégration dans une interface
utilisateur reste à réaliser.

Deux précisions importantes :

- l’OCR est nécessaire aux exports qui convertissent des sous-titres DVB,
  tandis que le pipeline historique d’encodage peut fonctionner sans
  CCExtractor ;
- Docker est requis lorsque le lanceur `bin/video_encoder_ccextractor` est
  utilisé, mais le cœur de l’application continue d’accepter tout exécutable
  compatible configuré avec `CCEXTRACTOR_EXECUTABLE`.
