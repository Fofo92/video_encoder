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

La conversion facultative des sous-titres DVB nécessite également :

- CCExtractor avec prise en charge OCR ;
- Tesseract ;
- les données linguistiques françaises de Tesseract.

L’exécutable CCExtractor peut être installé sur le système ou fourni par un
adaptateur, par exemple un lanceur utilisant une image Docker.

## Installation

```bash
git clone https://github.com/Fofo92/video_encoder.git
cd video_encoder
bundle install
```

Adapte ensuite `config/video_encoder.yml` à ton environnement, notamment :

- le chemin de la base SQLite ;
- la racine de la médiathèque ;
- les répertoires de travail ;
- le profil FFmpeg.

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

## Contrôle qualité

Le contrôle standard vérifie les dépendances Ruby, RuboCop et les tests
unitaires :

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

- la phrase sur l’OCR « facultatif » décrit la capacité technique ; l’encodage historique peut fonctionner sans CCExtractor ;

- Docker n’est pas présenté comme une dépendance d’exécution obligatoire : il constitue actuellement un moyen pratique de fournir CCExtractor avec Tesseract français.
