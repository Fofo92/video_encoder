# Editing Workflow

## Objectif

Ce document décrit le processus métier de construction d'un TrimProject. Il constitue le vocabulaire fonctionnel de video_encoder et sert de référence pour la conception du modèle de domaine.

Il ne décrit ni l'implémentation technique, ni les outils utilisés (MLT, FFmpeg, etc.), mais la manière dont un utilisateur sélectionne les portions d'un média qu'il souhaite conserver.

Cette description constitue le vocabulaire métier de `video_encoder`.

---

# Principes

L'utilisateur ne construit pas directement le média final.

Il construit progressivement un **TrimProject**, constitué des différentes portions du ou des médias d'origine qu'il souhaite conserver.

Une fois le projet terminé, celui-ci est exporté pour produire le média final.

La frontière entre la construction du projet et son export est volontairement nette.

```text
Médias source
      │
      ▼
 Construction du TrimProject
      │
      ▼
 TrimProject validé
      │
      ▼
 TrimExporter
      │
      ▼
 Média final
```

---

# Flux de travail

Le flux de travail (ou _workflow_) décrit les gestes. Les classes ne sont que les outils qui permettent de les accomplir.

## 1. Charger les médias

Le cas général consiste à charger un unique enregistrement.

Cependant, plusieurs médias peuvent être utilisés lorsqu'il est nécessaire de
combiner des portions provenant de sources différentes.

C'est notamment le cas lorsqu'un média déjà monté contient une portion
manquante et qu'un autre enregistrement permet ultérieurement de la remplacer.

Chaque média reste une source indépendante. Les positions de montage sont
exprimées dans le référentiel d'images propre à chaque source.

À ce stade, aucun découpage n'est encore réalisé.

## 2. Explorer un média

Un **moniteur de clip** permet de naviguer dans le média sélectionné.

L'utilisateur peut :

* avancer ;
* reculer ;
* accélérer la lecture ;
* se déplacer librement dans le média.

Cette étape ne modifie jamais le projet.

Elle sert uniquement à rechercher les portions intéressantes.

---

## 3. Définir une portion à conserver

Lorsqu'une première image d'une séquence intéressante est atteinte, l'utilisateur définit un point d'entrée (*In*).

Il poursuit ensuite sa lecture jusqu'à la dernière image à conserver avant la publicité (ou toute autre portion à supprimer), puis définit un point de sortie (*Out*).

### Montage à l'image près

La sélection est réalisée **à l'image près**.

L'image constitue l'unité élémentaire du montage. Les points d'entrée (*In*) et de sortie (*Out*) désignent des images précises du média.

Les horodatages (timecodes) servent à identifier et à afficher ces positions, ainsi qu'à dialoguer avec les outils techniques (MLT, FFmpeg, etc.). Ils ne constituent pas le concept métier fondamental.

Les bornes d'un segment sont inclusives : le point (*In*) désigne la première image visible conservée et le point (*Out*) la dernière image visible conservée.

Toute frontière de montage coïncide ainsi avec une image. Une coupure ne peut pas se situer entre deux images.

Une fois les deux bornes validées, un **Segment** est créé et ajouté au **TrimProject**.

---

## 4. Construire progressivement le projet

Les étapes précédentes sont répétées autant de fois que nécessaire jusqu'à couvrir l'ensemble du programme.

Chaque segment validé est ajouté à la timeline du **TrimProject**.

Dans le cas le plus simple, les segments sont placés successivement dans l'ordre du montage.

Il peut cependant être nécessaire de conserver volontairement un intervalle entre deux segments, par exemple lorsqu'une portion de mauvaise qualité a été supprimée et qu'aucun enregistrement de remplacement n'est encore disponible.

Cet intervalle constitue un **Gap**. Il correspond, dans le média final, à une image noire accompagnée de silence.

L'utilisateur peut exprimer la longueur de ce blanc sous la forme d'une durée. L'unité interne du montage restant l'image, cette durée est convertie en un nombre entier d'images selon la cadence vidéo du média.

La timeline peut ainsi être constituée, par exemple, de :

```
Segment A
    ↓
   Gap
    ↓
Segment B
```

### Remplacer une portion manquante depuis une autre source

Lorsqu'un autre enregistrement devient disponible, il peut fournir une portion
permettant de remplacer un **Gap**.

Le média contenant le **Gap** et le média de remplacement peuvent être explorés
simultanément dans deux moniteurs de clip.

Le remplacement ne consiste pas nécessairement à substituer au **Gap** une
portion de même durée.

L'utilisateur recherche visuellement deux raccords pertinents entre les
sources, par exemple à l'occasion d'un changement de scène.

Le premier raccord détermine :

* la dernière image conservée avant l'insertion ;
* la première image conservée dans le média de remplacement.

Le second raccord détermine :

* la dernière image conservée dans le média de remplacement ;
* la première image reprise dans le média d'origine.

Ainsi, à partir d'un média contenant :

```text
[ Segment A ][ Gap ][ Segment B ]
```

et d'une portion sélectionnée dans un autre média, le nouveau montage peut devenir :

```text
[ Segment A′ ][ Segment C ][ Segment B′ ]
```

`Segment C` possède un point d'entrée (*In*) et un point de sortie (*Out*) dans son propre média source.

Sa durée est indépendante de celle du **Gap**. Il peut donc être plus court,  égal ou plus long que celui-ci. Dans ce dernier cas, les raccords peuvent également raccourcir les portions adjacentes du média d'origine.

Les segments du nouveau `TrimProject` conservent chacun la référence au média source dont ils
proviennent. Leurs positions en images sont définies dans le référentiel de cette source.

Le **TrimProject** devient progressivement la représentation métier complète du montage.

---

## 5. Prévisualiser le projet

Un **moniteur de projet** permet de parcourir le montage obtenu.

Contrairement au moniteur de clip, celui-ci présente le montage tel qu'il est décrit par la timeline du **TrimProject**, notamment les segments retenus et les éventuels intervalles qui les séparent.

Cette étape permet de vérifier la cohérence du projet avant son export.

---

## 6. Exporter le projet

Lorsque le montage est validé, le **TrimProject** est considéré comme terminé.

Son rôle s'arrête ici.

Le projet est alors confié à **TrimExporter**, chargé de produire le média final.

Le processus d'export (génération MLT, rendu, remultiplexage...) est volontairement indépendant du processus de construction du projet.

---

# Principes d'architecture

Le workflow repose sur une séparation claire des responsabilités.

| Élément         | Responsabilité                                   |
| --------------- | ------------------------------------------------ |
| Clip Monitor    | Naviguer dans un média source.                   |
| TrimProject     | Décrire les portions des médias à conserver.     |
| Project Monitor | Prévisualiser le montage.                        |
| TrimExporter    | Produire le média final à partir du TrimProject. |

Cette séparation permet de faire évoluer indépendamment :

* l'interface utilisateur ;
* les méthodes de sélection (manuelle ou automatique) ;
* les mécanismes d'export.

Le **TrimProject** reste ainsi une représentation purement métier du montage, indépendante des outils techniques utilisés pour produire le média final.
