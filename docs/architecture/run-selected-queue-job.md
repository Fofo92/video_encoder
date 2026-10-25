# Exécuter seulement la tâche sélectionnée

Dans la file, sélectionner une tâche **En attente**, puis cliquer sur
**Lancer uniquement la sélection**. La tâche est exécutée à sa position actuelle,
sans déplacer ni reporter les autres et sans poursuivre la file à sa fin, même
si elle échoue. L’affichage garde le suivi habituel de progression.

Le bouton est désactivé si un encodage de la file est en cours, si aucune tâche
n’est sélectionnée ou si elle n’est pas en attente. Une tâche reportée doit être
réactivée ; une tâche échouée ou interrompue doit être remise en attente.
La disponibilité est revérifiée au lancement, puis lors de la prise en charge.
La vérification habituelle des workers actifs s’applique aussi à ce lancement.

Le même mode est accessible en ligne de commande :

```sh
bin/video_encoder run-trim-exports --job IDENTIFIANT
```

`--job` est distinct de `--once` : ce dernier traite toujours la file d’attente
selon son fonctionnement habituel. Aucun changement de schéma de base n’est requis.
