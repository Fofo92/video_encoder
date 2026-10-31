# Conservation et suppression des captures en quarantaine

Les captures mises en quarantaine par `quarantine-source --confirm` sont désormais
enregistrées dans la base SQLite de la file (`quarantine_sources`). La date UTC
effective de déplacement démarre un délai de **30 jours de 24 heures**. La table
est créée automatiquement, sans modification des tâches existantes. Sauvegarder
la base de la file conserve les dates et le journal des suppressions.

## Conditions cumulatives de suppression automatique

- Source régulière `.m2t`, `.ts`, `.mts` ou `.m2ts`, directement dans le répertoire
  de quarantaine configuré ; identité, taille et date de modification inchangées.
- Source absente de son ancien emplacement.
- Tous les couples projet/résultat connus pour cette source sont présents et
  cohérents : projets reconnus, sources concordantes, résultats non vides.
- Encodage achevé confirmé par un reçu d’export valide (empreinte du projet,
  chemin, taille et date du résultat), ou par une tâche `done` pour ce couple si
  aucun reçu n’existe. Un reçu présent mais invalide ne bénéficie pas du repli.
- Aucun projet ou résultat modifié depuis la dernière preuve mémorisée ; aucune
  tâche `queued`, `running` ou `deferred` ne dépend de la source, même via un autre
  chemin du même fichier. Aucun espace de travail d’export n’est présent.
- Délai atteint. Un projet actif illisible bloque la vérification plutôt que de
  laisser supposer qu’il n’utilise pas la capture.

La mise en quarantaine capture la liste des projets connue dans la file, même si
leur vérification est incomplète. Pour un même projet, le dernier export achevé
est retenu ; la sortie absente d’une tentative échouée ne devient pas un prérequis.
Les nouvelles références découvertes ensuite
s’y ajoutent. On protège donc chaque montage connu issu d’une capture contenant
plusieurs émissions. Les projets jamais inscrits dans la file doivent être
associés explicitement lors du suivi d’un ancien fichier. Ce contrôle technique
ne remplace pas la confirmation initiale que toutes les émissions utiles d’une
source ont été montées.

La suppression et sa dernière vérification tiennent une transaction SQLite
`immediate`, commune à la file : une tâche ne peut pas démarrer ou être ajoutée
pendant cette vérification. Les fichiers source seuls sont effacés ; les projets,
résultats encodés, reçus, tâches et anciennes lignes de suivi sont conservés.
Un échec de journalisation du déplacement conserve le fichier original et retire
le lien nouvellement créé en quarantaine.

## Fichiers déjà présents

Ils restent **sans échéance tant que les preuves sont insuffisantes**. Le contrôle
quotidien peut activer automatiquement le suivi après avoir retrouvé tous les
couples projet/résultat connus dans la file et vérifié leur cohérence : il démarre
alors un délai **neuf de 30 jours**, sans utiliser l’ancien `mtime` et sans demander
de confirmation manuelle. Une origine ambiguë ou une preuve insuffisante laisse
la source sans échéance avec un motif d’examen.

Dans Sources → Suivi de la quarantaine, « Activer le suivi de la sélection
(30 jours) » permet d’effectuer cette vérification immédiatement. « Associer un
projet… » permet de fournir un projet JSON absent de la file : son résultat de
même nom `.mkv` doit avoir un reçu d’export cohérent. Tous les autres projets
connus dans la file sont également vérifiés.

## Commandes et aperçu

```sh
bundle exec ruby bin/video_encoder quarantine list
bundle exec ruby bin/video_encoder quarantine sweep
bundle exec ruby bin/video_encoder quarantine enroll '/commun/Quarantaine/Film.m2t'
bundle exec ruby bin/video_encoder quarantine enroll '/commun/Quarantaine/Film.m2t' --project '/videos/Film.json'
bundle exec ruby bin/video_encoder quarantine sweep --apply
```

`list` et `sweep` sans `--apply` ne suppriment rien et ne démarrent aucun délai.
`sweep --apply` active aussi les anciens fichiers vérifiables, avec un délai
neuf ; les autres restent conservés.
La vue Sources → Suivi de la quarantaine présente les dates en heure locale,
les motifs de conservation et l’état du minuteur. Son aperçu est également
strictement sans suppression. Les dates indiquent le premier instant éligible ;
la suppression a lieu au passage suivant du minuteur si tous les contrôles passent.

## Activation quotidienne, indépendante de l’IHM

Depuis le dépôt, dans le terminal habituel où `bin/check` fonctionne :

```sh
python3 bin/install-quarantine-timer
```

L’installateur vérifie Ruby/Bundler par un aperçu, puis installe un service et un
minuteur **utilisateur**, sans sudo. Il reprend le PATH et l’environnement Ruby
du terminal. Contrôle quotidien à 03 h 30, rattrapage à l’ouverture de session si
une exécution a été manquée. Il fonctionne sans lancer ou redémarrer l’IHM.
Le service utilise ce dépôt, sa configuration et sa base de file habituelles.
L’installation ne lance pas l’IHM et ne redémarre aucun encodage. Un minuteur déjà
échu peut lancer immédiatement le service : les fichiers sans date vérifiables démarrent alors leur délai de 30 jours.

```sh
systemctl --user list-timers video-encoder-quarantine.timer --no-pager
journalctl --user -u video-encoder-quarantine.service -n 50 --no-pager
systemctl --user disable --now video-encoder-quarantine.timer
```

Le service ne supprime pas la corbeille `.video_encoder_trash` des projets,
qui conserve sa gestion manuelle indépendante. La suppression automatique d’une
capture est définitive : la quarantaine ne constitue pas une sauvegarde.
