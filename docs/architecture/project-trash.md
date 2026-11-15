# Corbeille des projets

Projets → Corbeille des projets présente une ligne par suppression : projet,
date, taille logique des fichiers regroupés, emplacement initial. La sélection
multiple permet de restaurer ou de supprimer définitivement plusieurs projets.
Vider la corbeille concerne toutes les lignes connues et accessibles, avec
confirmation négative par défaut. Le service quotidien de quarantaine purge aussi
les entrées vérifiées âgées de 30 jours.

Les racines `.video_encoder_trash` sont mémorisées dans la table
`project_trash_roots` de la base de la file d'encodage. Cette petite table est
créée à la première utilisation. Le chemin est enregistré lors de la suppression,
avant déplacement des fichiers. Aucun parcours récursif des disques n'est lancé.
Pour une corbeille créée avant ce mécanisme, Ajouter un dossier permet de choisir
son dossier parent ou le dossier `.video_encoder_trash` lui-même.

Un volume indisponible ou un manifeste invalide est signalé dans la vue. Vider
est alors désactivé pour ne pas prétendre vider une corbeille incomplètement
connue. Les autres entrées valides restent traitables individuellement. Un
contenu invalide demande une vérification manuelle, jamais un effacement récursif.

Chaque action transmet le jeton du contenu affiché. Sous transaction SQLite
immédiate, le service recharge le manifeste, contrôle les fichiers et vérifie
les références de la file active, y compris ses sources. Les liens symboliques,
les chemins sortant du dossier de récupération et les fichiers inattendus sont
refusés. Les actions de gestion sont désactivées tant qu'un éditeur est ouvert.

La restauration vérifie tous les chemins initiaux et utilise des liens physiques
exclusifs : aucun fichier existant ne peut être écrasé, même s'il apparaît après
la vérification. Une erreur lors de la création des liens annule les liens déjà
créés, sans retirer les fichiers de la corbeille. Les fichiers restaurés sont
ensuite retirés de la corbeille. Les dépendances restent sur le même volume,
conformément à la suppression récupérable initiale.

Une suppression définitive retire uniquement les fichiers réguliers énumérés
par le manifeste validé, puis le manifeste et son dossier vide. Une erreur de
permissions ou d'entrée/sortie peut laisser une opération partielle, signalée
par la vue. Une sélection multiple traite les entrées séparément et rapporte
les erreurs sans annuler les autres résultats. La confirmation précise la taille
logique sélectionnée ; l'espace effectivement récupéré dépend du système de fichiers.

Commandes disponibles :

```text
video_encoder project-trash list
video_encoder project-trash register /dossier/.video_encoder_trash
video_encoder project-trash restore /dossier/.video_encoder_trash/UUID TOKEN
video_encoder project-trash purge /dossier/.video_encoder_trash/UUID TOKEN
```

Les jetons proviennent de `list` ; les commandes mutantes ne peuvent pas agir
sur un dossier non enregistré. L'historique des tâches est conservé et aucun
enregistrement n'est reprogrammé lors d'une restauration.

## Rétention automatique

Le même service utilisateur `video-encoder-quarantine.service`, déclenché à 03 h 30,
traite successivement les captures et les corbeilles de projets. Un échec du premier
traitement ne saute pas le second ; le service rapporte néanmoins un échec.

Le délai est de 30 jours depuis la création du dossier de récupération. Si le
système ne fournit pas cette date, la date du manifeste créé lors de la suppression
sert de référence. Les anciennes entrées enregistrées sont concernées avec cette
date, sans recommencer le délai au déploiement. Une modification de la vidéo ne
réinitialise pas le délai. Aucun parcours récursif de `/videos` n’est effectué.
Les racines anciennes non enregistrées restent ajoutables dans la corbeille.

```sh
bin/video_encoder project-trash sweep          # aperçu, aucune suppression
bin/video_encoder project-trash sweep --apply  # purge des seules entrées échues et vérifiées
bin/install-quarantine-timer                   # aperçu puis mise à jour du même service/minuteur
```

L’aperçu affiche `created_at`, `delete_after` et un état `scheduled`, `due` ou
`blocked`. Les dossiers invalides restent conservés. Avant chaque purge, le service
recharge les fichiers, contrôle leur jeton, revalide l’âge et les tâches actives
sous le verrou SQLite commun. Les fichiers inattendus, liens symboliques et
références actives empêchent la purge. Les tâches historiques restent conservées.
La suppression porte uniquement sur les fichiers du manifeste, puis le manifeste
et son dossier vide ; elle n’utilise pas de suppression récursive.
