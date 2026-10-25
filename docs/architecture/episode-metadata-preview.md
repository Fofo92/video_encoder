# Prévision linguistique et complément de fiche

La passerelle transmet une prévision VF si chaque source inspectée possède une seule
piste audio française, ou une seule piste non renseignée/und selon la convention de
la bibliothèque. Une inspection absente, une piste d’audiodescription, plusieurs pistes
ou une autre langue ne donnent pas lieu à une supposition automatique. Les rôles et
pistes finaux restent déterminants après encodage ; cette prévision reste modifiable.

La requête n’envoie que la valeur courte VF, pas l’inspection complète ni les médias.
Les clients plus anciens peuvent omettre cette information et continuent à fonctionner.

La confirmation de destination d’un épisode indique les métadonnées manquantes et
propose « Compléter la fiche dans vidb ». Le lien doit rester sur le serveur vidb configuré.
Le montage reste ouvert pendant la consultation et peut être enregistré après retour.
Le résultat de l’encodage n’est pas conditionné par la complétude des métadonnées.
