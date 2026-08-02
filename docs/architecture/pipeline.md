# Pipeline de traitement# Pipeline de traitement

## Objectif

Le pipeline décrit le traitement complet d'un enregistrement TNT, depuis le fichier brut jusqu'au média final prêt à être diffusé ou catalogué.

Chaque étape possède une responsabilité unique et échange avec les suivantes au moyen d'objets métier plutôt que par des commandes **FFmpeg**.

## Vue d'ensemble

```
Enregistrement TNT
        │
        ▼
      trim
(découpage sans perte)
        │
        ▼
   MediaProbe
(analyse du média)
        │
        ▼
 TrackSelector
(sélection des pistes)
        │
        ▼
    Encoder
(encodage vidéo)
        │
        ▼
    Verifier
(validation)
        │
        ▼
  Workspace
(finalisation)
        │
        ├──────────────► MiniDLNA
        │
        └──────────────► vidb
```

## Étapes

### Trim

Produit un nouveau média à partir des portions de l'enregistrement à conserver.

Cette étape est indépendante de l'encodage et repose sur un modèle métier (`TrimProject`) décrivant les segments conservés.

Voir : `trim.md`

---

### MediaProbe

Analyse le média obtenu et construit un objet `Media`.

Aucun choix n'est effectué à cette étape : toutes les pistes sont décrites fidèlement.

---

### TrackSelector

Applique les règles métier de sélection des pistes.

Il détermine :

- la piste vidéo à conserver ;
- les pistes audio ;
- les sous-titres éventuels.

Les règles de sélection sont décrites dans :

`docs/domain/track_selection.md`

---

### Encoder

Construit et exécute la commande d'encodage à partir :

- du média analysé ;
- des pistes sélectionnées ;
- des paramètres d'encodage.

Voir : `encoding.md`

---

### Verifier

Contrôle le média produit.

Il vérifie notamment :

- la présence des pistes attendues ;
- les caractéristiques générales du média.

---

### Workspace

Finalise le traitement.

Cette étape est responsable :

- du renommage du fichier temporaire ;
- du nettoyage des fichiers intermédiaires ;
- de la mise à disposition du média final.

## Principes

Le pipeline sépare clairement :

- les règles métier ;
- la description des médias ;
- les traitements techniques.

Chaque étape ne possède qu'une seule responsabilité.
