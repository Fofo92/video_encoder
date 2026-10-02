# Design patterns

## Repository

### Contexte

`video_encoder` manipule des `TrimExportJob` dont l’état doit être conservé
entre deux exécutions.

Le reste de l'application ne doit pas connaître le mécanisme de stockage
utilisé.

### Mise en œuvre

La persistance est confiée à `JobRepository`, qui constitue l'unique point
d'accès aux données des jobs.

Les composants applicatifs manipulent uniquement des `TrimExportJob` et
délèguent leur sauvegarde ou leur chargement au Repository.

### Motivation

Cette séparation présente plusieurs avantages :

- le domaine métier reste indépendant du stockage ;
- les tests sont simplifiés grâce au découplage ;
- le mécanisme de persistance pourra évoluer sans impacter les traitements.

Cette approche correspond au pattern **Repository**.
Les principes généraux de ce pattern sont décrits dans la documentation
d'ingénierie logicielle (`dev-notes`).
