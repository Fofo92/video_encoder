# Encodage

## Objectif

Le module d'encodage transforme un média analysé en un nouveau média conforme aux paramètres de compression retenus.

Il ne décide jamais quelles pistes doivent être conservées.

Cette décision appartient au `TrackSelector`.

## Entrées

L'encodeur reçoit :

- un objet `Media` décrivant le média source ;
- la sélection produite par `TrackSelector` ;
- les paramètres d'encodage.

## Responsabilités

L'encodeur est responsable de :

- construire la commande FFmpeg ;
- lancer l'encodage ;
- produire un fichier temporaire.

Il n'effectue :

- aucune analyse du média ;
- aucune sélection de pistes ;
- aucune décision métier.

## Sortie

L'encodage produit un média temporaire destiné à être :

- vérifié ;
- puis validé par `Workspace`.

## Principes

L'encodeur est indépendant :

- des règles de sélection des pistes ;
- du catalogue (`vidb`) ;
- du processus de découpage (`trim`).

Sa responsabilité est uniquement la transformation technique du média.

## Relations

```
MediaProbe
      │
      ▼
    Media
      │
      ▼
TrackSelector
      │
      ▼
 sélection
      │
      ▼
   Encoder
      │
      ▼
 fichier temporaire
      │
      ▼
  Verifier
```

Les choix métier sont réalisés avant l'encodage.

L'encodeur applique ces décisions sans les modifier.
