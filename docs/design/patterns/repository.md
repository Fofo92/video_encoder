# Repository

## Contexte

`video_encoder` manipule des objets métier (`Job`) dont l'état doit être
persisté entre deux exécutions.

Les traitements de l'application ne doivent pas connaître le mécanisme de
stockage utilisé.

## Mise en œuvre

La persistance est confiée à `JobRepository`, qui constitue l'unique point
d'accès aux données des jobs.

Les composants métier manipulent uniquement des objets `Job` et délèguent leur
chargement et leur sauvegarde au Repository.

Ils ne connaissent ni le format des fichiers utilisés ni leur emplacement.

## Motivation

Cette séparation présente plusieurs avantages :

* le domaine métier reste indépendant du stockage ;
* les tests sont simplifiés grâce au découplage ;
* le mécanisme de persistance peut évoluer sans impacter les traitements.

Cette mise en œuvre correspond au pattern **Repository**.
