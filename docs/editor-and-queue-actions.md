# Bornes, tâches et destinations

## Modification des bornes

Le sélecteur possède trois modes : **Navigation**, **Modifier IN**, **Modifier OUT**.
La modification concerne exclusivement le segment sélectionné. Choisir un mode
de modification charge ses bornes dans les repères. Basculer entre IN et OUT
conserve les ajustements non appliqués. **Ctrl+← / Ctrl+→** et **−1 / +1** décalent
la borne choisie d'une image. **Appliquer** (Entrée) remplace le segment à sa place.

En mode Navigation, les commandes de décalage sont grisées. En mode modification,
la pose de nouveaux repères, la création avec coupures, la sauvegarde et la mise
en file sont grisées jusqu'à l'application ou au retour en Navigation.
Revenir à Navigation, ou sélectionner un autre segment, abandonne les ajustements
non appliqués. Les segments déjà enregistrés restent inchangés.

Le curseur de lecture prend la couleur rouge d'une borne lorsqu'il est placé
exactement sur IN, OUT ou une extrémité de segment. Une image avant ou après,
il retrouve sa couleur de navigation.

## File d'attente

| Action | Éligibilité | Effet |
|---|---|---|
| Reporter | En attente | Conserver la même tâche, exclue des lancements jusqu'à réactivation |
| Réactiver | Reportée | Remettre la même tâche en attente, sans créer de doublon |
| Destination… | En attente ou reportée, file arrêtée | Modifier nom et dossier du MKV ; créer son JSON correspondant sans supprimer l'ancien |
| Supprimer la tâche | Toute tâche non active | Retirer la tâche de la liste, conserver tous les fichiers |
| Supprimer tâche et JSON… | Tâche non active, JSON présent | Après confirmation, supprimer aussi le JSON s'il n'est utilisé par aucune autre tâche |

Les fichiers sources, MKV et reçus d'export ne sont jamais supprimés par ces actions.
La suppression explicite du JSON est définitive ; ce n'est pas un déplacement
dans la corbeille du bureau. L'ancien bouton **Retirer de la file** supprimait
la tâche ; il ne la reportait pas. Il est renommé **Supprimer la tâche**.

Les tâches reportées sont visibles dans l'onglet **Reportés** et dans **Tous**.
Elles continuent de protéger leurs sources contre un déplacement en quarantaine
tant qu'elles dépendent de ces fichiers.
Les tâches en cours ne peuvent être reportées, renommées ni supprimées.
Les gardes en base empêchent une action devenue inapplicable parce que le worker
vient de démarrer la tâche. La prise en charge est conditionnelle et atomique :
un worker ignore une tâche qui a été reportée ou supprimée depuis sa sélection.

Le changement de destination refuse un MKV existant, une sortie réservée par une
autre tâche et un JSON différent déjà présent au nouvel emplacement. Il conserve
l'identité, l'état et les tentatives de la tâche. Le worker relit la destination
persistée après l'avoir prise en charge.

## Remise en file d'un projet chargé

**Ajouter à la file** propose désormais le choix du nom et du dossier du MKV,
même lorsque le projet est déjà enregistré. La confirmation audio affiche cette
destination. L'archivage habituel place une copie du projet à côté du MKV prévu.

## Vérifications

```bash
bundle exec rspec spec/persistence/job_repository_spec.rb \
  spec/persistence/job_repository_queue_actions_spec.rb \
  spec/trim_export_worker_spec.rb spec/trim_export_worker_queue_race_spec.rb
PYTHONPATH=ui QT_QPA_PLATFORM=offscreen python3 -m unittest discover \
  -s ui/tests -p 'test_trim_export_queue*.py'
PYTHONPATH=ui QT_QPA_PLATFORM=offscreen python3 -m unittest discover \
  -s ui/tests -p 'test_queue_usability.py'
PYTHONPATH=ui QT_QPA_PLATFORM=offscreen python3 -m unittest discover \
  -s ui/tests -p 'test_application_marker_nudge.py'
PYTHONPATH=ui QT_QPA_PLATFORM=offscreen python3 -m unittest discover \
  -s ui/tests -p 'test_application_audio_preflight.py'
PYTHONPATH=ui QT_QPA_PLATFORM=offscreen python3 -m unittest discover \
  -s ui/tests -p 'test_widgets.py'
```
