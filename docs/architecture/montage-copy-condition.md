# État de la copie issue d’un montage

Avant l’identification vidb ou le choix de la destination d’un export, une
déclaration décrit le résultat conservé : complétude et détérioration sont
indépendantes. Les valeurs proposées au premier passage sont complète et sans
détérioration. Un défaut retiré au montage ou remplacé par une autre source ne
doit pas être signalé sur le résultat.

Le menu Montage → État de la copie à encoder… permet de revoir cette déclaration.
Elle comporte une note facultative et, si utile, la source concernée. Un nouveau
passage est demandé si la liste des sources effectivement utilisées change.
Annuler conserve la déclaration précédente et interrompt la préparation.

`copy_condition` est conservé dans le JSON du projet, à sa réouverture et lors
de la préparation d’un réencodage. Aucun état n’est inventé à la lecture d’un
ancien projet : une confirmation est demandée à sa prochaine préparation.
Les fichiers et leurs noms ne sont pas modifiés par la déclaration elle-même.
Il faut enregistrer le projet pour la conserver sur disque.

Le reçu d’export final transporte cette déclaration vers vidb, qui l’applique
uniquement à la nouvelle copie lors de son import. L’identification ne crée
aucune copie disponible. Les autres copies et l’état de visionnage sont conservés.
Un ancien reçu sans déclaration conserve le comportement historique de vidb.

« Incomplète » sans précision ne signifie ni début ni fin. Aucune durée conservée
n’est déduite du texte libre ou de la durée du fichier. Ces valeurs peuvent être
qualifiées plus précisément dans vidb. Les versions linguistiques et les pistes
audio/sous-titres ne sont pas modifiées par ce mécanisme.
