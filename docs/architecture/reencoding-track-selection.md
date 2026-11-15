# Réencoder un projet en modifiant ses pistes

Le menu Montage propose « Réencoder en file d’attente… ». Il reprend
les sources et les segments du montage ouvert, même si une sortie existe déjà.
La sélection VF / VM / VMST précède le choix de destination et le contrôle audio.
Elle ne réutilise pas automatiquement une ancienne décision VF.
Après le contrôle audio et sa confirmation, le nouvel export est ajouté à la
file existante. Il ne démarre pas d’encodeur indépendant et attend son tour si
un autre job est déjà en cours.

Les pistes sont sondées sur toutes les sources effectivement utilisées. Les
profils indisponibles restent désactivés. VMST exige l’audio français, le rôle
original `qaa` et des sous-titres français ordinaires ; les sous-titres forcés
seuls ou pour malentendants ne suffisent pas. Les règles du moteur Ruby restent
chargées d’exporter les pistes et d’en vérifier l’exploitabilité.

La proposition de destination est distincte de l’ancien fichier, avec la version
demandée dans son nom. Un nouveau JSON est créé sans écrasement ; l’ancien
projet, son compte rendu et sa vidéo sont conservés. Les segments et l’identité
du projet restent les mêmes : chaque sortie possède son propre compte rendu
et sa propre empreinte de projet. Les imports vidb distinguent les copies par
leur chemin et leur compte rendu.

Lorsque la langue est incertaine et qu’aucun choix valide n’est déjà enregistré,
la préparation normale préfère VMST si les pistes compatibles sont présentes
sur toutes les sources utilisées. La proposition transmise à vidb est aussi
VMST lorsque les inspections disponibles l’étayent. Une décision explicite déjà enregistrée reste
respectée ; l’action de réencodage permet de la revoir. Une VO clairement
française ne devient pas VMST sur la seule présence de `qaa`.

La source originale doit rester accessible. Aucun procédé ne peut retrouver
une piste absente de l’ancienne sortie à partir de cette sortie seule.
