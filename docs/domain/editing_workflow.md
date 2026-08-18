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

L'utilisateur ouvre un ou plusieurs médias.

Le cas général consiste à charger un unique enregistrement.

Cependant, plusieurs médias peuvent être utilisés lorsque plusieurs enregistrements partiels d'une même émission doivent être combinés afin de reconstituer un programme complet.

À ce stade, aucun découpage n'est encore réalisé.

---

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

Le **TrimProject** devient progressivement la représentation complète du montage à produire.

Il constitue la description métier du montage.

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
| TrimProject     | Décrire les portions du média à conserver.       |
| Project Monitor | Prévisualiser le montage.                        |
| TrimExporter    | Produire le média final à partir du TrimProject. |

Cette séparation permet de faire évoluer indépendamment :

* l'interface utilisateur ;
* les méthodes de sélection (manuelle ou automatique) ;
* les mécanismes d'export.

Le **TrimProject** reste ainsi une représentation purement métier du montage, indépendante des outils techniques utilisés pour produire le média final.
