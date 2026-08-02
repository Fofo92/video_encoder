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
