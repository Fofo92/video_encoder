# Confirmer la fin d’utilisation d’une source

Un encodage réussi ne suffit pas à déclarer une source entièrement traitée : elle
peut contenir un autre programme dont le montage n’existe pas encore.

L’application surveille les nouvelles tâches terminées pendant son ouverture.
Après un encodage direct ou un encodage dans la file, elle propose une question
non bloquante lorsque les travaux connus n’utilisent plus cette source.

- « Il reste un programme ou un doute : conserver la source » est le choix par défaut.
- Fermer la question conserve également la source.
- « Tout est encodé : mettre la source en quarantaine » est une confirmation
  humaine que tous les programmes utiles ont effectivement été encodés.

La question n’arrête pas la file. Les tâches en attente, en cours, différées,
échouées ou interrompues qui référencent cette source empêchent sa proposition.
Avant le déplacement, la file est relue et les identités de la source et des
sorties présentes sont comparées avec celles affichées. Le déplacement utilise
ensuite la commande habituelle `quarantine-source --confirm`, qui contrôle à
nouveau les travaux actifs et refuse l’écrasement d’une destination existante.

Le menu Sources → Examiner les sources encodées… permet de reprendre une décision
différée, y compris pour les anciens travaux de la file. Au démarrage, l’historique des
tâches déjà terminées ne déclenche pas une rafale de questions.

Seules les captures `.m2t`, `.mts` et `.ts` sous `/commun/to_be_cut` sont proposées.
Les projets et vidéos restent en place ; les sources confirmées sont déplacées
vers le répertoire de quarantaine configuré, habituellement `/commun/Quarantaine`.
Les choix de conservation restent implicites dans la présence de la source :
aucun reçu JSON supplémentaire n’est produit et aucune autorisation de déplacer
automatiquement cette source lors d’un prochain encodage n’est mémorisée.

Pour un montage multisource, chaque capture éligible est proposée successivement.
Confirmer ou conserver la première ne décide rien pour les autres. Une source
encore utilisée par une autre tâche reste protégée ; elle peut être proposée
lorsque cette tâche ne la bloque plus. Le suivi des réponses distingue la source
et les travaux terminés qui l’utilisent : il ne repose pas seulement sur le numéro
du travail multisource. Un nouvel export de cette source permet une nouvelle
question, même si la source avait été conservée auparavant.

Ce protocole ne supprime aucun fichier de quarantaine. Le délai et les conditions
de purge devront être fixés avant d’activer cette seconde étape.
