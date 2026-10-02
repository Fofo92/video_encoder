# Repository

## Contexte

`video_encoder` manipule des `TrimExportJob` dont l’état doit être conservé
entre deux exécutions. Les traitements de l’application ne doivent pas
connaître le mécanisme de stockage utilisé.

## Mise en œuvre

La persistance est confiée à `JobRepository`, qui constitue l’unique point
d’accès à la file des exports.

Les composants applicatifs manipulent uniquement des `TrimExportJob` et
délèguent au Repository leur création, leur sélection et leurs changements
d’état. Ils ne connaissent ni le schéma SQLite ni son emplacement.

## Motivation

Cette séparation présente plusieurs avantages :

- le domaine métier reste indépendant du stockage ;
- les tests sont simplifiés grâce au découplage ;
- le mécanisme de persistance peut évoluer sans affecter les traitements.

Cette mise en œuvre correspond au pattern **Repository**.
