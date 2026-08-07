# Trim

## Objectif

Le module `trim` a pour objectif de produire un nouveau média constitué de plusieurs  portions d'un enregistrement TNT, sans que l'utilisateur ait à connaître les détails de **FFmpeg** ou de **MLT**.

Le résultat attendu est un fichier unique, prêt à être transmis au processus d'encodage.

------

## Modèle de domaine

### Segment

Un `Segment` représente une portion du média source à conserver.

Il est défini par :

- une position de début (`start_time`) ;
- une position de fin (`end_time`).

Invariants :

- la fin est strictement postérieure au début.

Comportement :

- il connaît sa durée.

------

### TrimProject

Un `TrimProject` représente un projet de découpage.

Il est constitué :

- d'un média source (`Media`) ;
- d'une liste ordonnée de `Segment`.

Invariants :

- les segments sont ajoutés dans l'ordre chronologique ;
- deux segments ne peuvent ni se chevaucher ni être contigus.

Comportement :

- il connaît sa durée totale.

Le `TrimProject` est indépendant de toute technologie de traitement vidéo.

------

## Architecture retenue

Le découpage repose sur une architecture hybride.

```
                TrimProject
                     │
                     ▼
              génération MLT
                     │
                     ▼
             rendu vidéo/audio
                     │
                     ▼
          remultiplexage FFmpeg
                     │
                     ▼
              média découpé
```

Les responsabilités sont réparties comme suit :

- **TrimProject** : description du découpage.
- **MLT** : application de la *timeline*.
- **FFmpeg** : assemblage final des flux.

------

## Principes

Le modèle métier ne dépend ni de **FFmpeg** ni de **MLT**.

Les composants techniques sont responsables de la transformation du `TrimProject` en commandes de traitement.
# Trim Pipeline

## Objectif

Le pipeline de découpage est responsable de la production d'un nouveau média à partir d'un enregistrement existant et d'une sélection de segments.

Il repose sur une séparation stricte entre :

* le modèle métier décrivant le découpage ;
* la traduction de ce modèle vers les outils techniques ;
* l'exécution des traitements de rendu.

Cette séparation permet de faire évoluer indépendamment les règles métier et les technologies utilisées pour réaliser le découpage.

---

# Vue d'ensemble

Le pipeline est organisé comme suit :

```text
                TrimProject
                     │
                     ▼
           MltProjectBuilder
                     │
                     ▼
               projet MLT
                     │
                     ▼
              MltRenderer
               ├──────────────┐
               ▼              ▼
        vidéo temporaire   audio(s)
               └──────┬───────┘
                      ▼
            FfmpegRemuxer
                      │
                      ▼
              média découpé
```

Chaque composant possède une responsabilité unique.

---

# Composants

## TrimProject

`TrimProject` est le modèle métier du découpage.

Il décrit :

* le média source ;
* les segments conservés ;
* leur durée totale.

Il garantit également les règles de cohérence du découpage :

* aucun segment vide ;
* aucun segment inversé ;
* aucun chevauchement ;
* au moins une image entre deux segments.

`TrimProject` ne connaît ni MLT, ni FFmpeg, ni le format de sortie.

---

## MltProjectBuilder

`MltProjectBuilder` traduit un `TrimProject` en un projet MLT minimal.

Sa responsabilité est exclusivement de produire la représentation XML de la timeline.

Il ne lance aucune commande externe.

---

## MltRenderer

`MltRenderer` exécute `melt` afin d'appliquer la timeline décrite dans le projet MLT.

Il produit les flux élémentaires nécessaires au média final :

* une vidéo temporaire ;
* une ou plusieurs pistes audio temporaires.

Il ne réalise aucun remultiplexage.

---

## FfmpegRemuxer

`FfmpegRemuxer` assemble les différents flux produits par MLT.

Il est responsable de :

* la sélection des flux à conserver ;
* leur remultiplexage ;
* la restauration des métadonnées (langues des pistes, etc.) ;
* la génération du média final.

Il ne connaît pas les segments du découpage.

---

# Répartition des responsabilités

Le pipeline applique le principe de responsabilité unique.

| Composant           | Responsabilité                                 |
| ------------------- | ---------------------------------------------- |
| `TrimProject`       | Décrire le découpage.                          |
| `MltProjectBuilder` | Construire la timeline MLT.                    |
| `MltRenderer`       | Produire les flux élémentaires.                |
| `FfmpegRemuxer`     | Assembler les flux et produire le média final. |

Aucun composant ne cumule plusieurs de ces responsabilités.

---

# Principes d'architecture

Le pipeline repose sur quelques principes simples.

## Le domaine est indépendant des outils

Le modèle métier ne dépend ni de MLT ni de FFmpeg.

Les objets métier peuvent être manipulés, testés et validés sans exécuter de commande externe.

---

## Les adaptateurs traduisent le domaine

Les composants techniques traduisent le modèle métier vers les outils utilisés.

Ils encapsulent les détails des formats, des commandes et des paramètres nécessaires au traitement.

---

## Les services techniques sont spécialisés

Chaque service technique réalise une seule opération :

* construire un projet MLT ;
* exécuter MLT ;
* remultiplexer les flux.

Cette spécialisation limite le couplage et facilite les évolutions futures.

---

# Évolutions

À ce stade, les différentes étapes du pipeline sont implémentées sous la forme de composants indépendants.

Une étape ultérieure introduira un orchestrateur chargé de coordonner ces composants afin de produire un média découpé complet à partir d'un `TrimProject`.

Cet orchestrateur ne portera aucune règle métier ; il assurera uniquement l'enchaînement des différentes étapes du pipeline.
