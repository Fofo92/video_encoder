# Confirmation de quarantaine périmée

La validation compare les sorties par chemin et identité de fichier, sans
dépendre de l’ordre des tâches renvoyées par la file. Un changement réel de
source, de sortie ou une tâche encore inachevée reste bloquant.

Lorsqu’une validation ou le backend refuse la quarantaine, l’ancienne question
est fermée avant l’avertissement. La source n’est pas déplacée par ce refus.
La confirmation et les sondages sont suspendus pendant cet avertissement afin
qu’un événement clavier ou le timer ne relance pas une question derrière lui.

Après acquittement, une source déjà examinée n’est pas immédiatement reproposée
avec les mêmes tâches terminées. Le menu Sources → Examiner les sources
encodées… permet de reconstruire une proposition actuelle ; une nouvelle fin
d’encodage peut également demander une nouvelle confirmation.
