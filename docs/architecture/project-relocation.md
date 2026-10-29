# Déplacement ou renommage d’un projet et de sa vidéo

Depuis l’accueil, choisir **Projets → Déplacer ou renommer un projet et sa vidéo…**.
Le travail sélectionné fournit le projet ; sans sélection, un sélecteur permet
de choisir un JSON qui n’a pas encore de tâche. Choisir ensuite le dossier cible
puis le nom commun sans extension. Conserver le dossier actuel pour renommer
seulement ; conserver le nom proposé pour déplacer seulement. Une prévisualisation
liste les fichiers et les sorties de la file avant confirmation (Non par défaut).
L’annulation ne modifie rien. L’exécution refait les contrôles après confirmation.

Fermer l’éditeur avant cette opération. Les projets employés par un encodage en
cours, les liens symboliques et les destinations déjà présentes sont refusés.
Un workspace restant doit être traité avant de déplacer son projet, afin de ne
pas perdre le contexte d’une reprise.

Le moteur Ruby déplace :

- le projet JSON, versions 1 et 2 ;
- ses sorties connues dans les tâches, si elles existent ;
- les vidéos de même nom MKV, M4V ou MP4, sauf si elles sont des sources du projet ;
- les reçus video_encoder-export.json associés, lorsqu’ils existent.

Le JSON est le projet de découpage : les bornes et les sources y sont stockées.
Il n’y a pas de fichier de découpage permanent supplémentaire à renommer.
Les fichiers MLT dans le workspace sont temporaires et seront régénérés ; un
workspace encore présent bloque l’opération, comme avant. Les fichiers annexes
créés manuellement ne sont pas renommés automatiquement.

Lors d’un renommage, chaque sortie conserve son extension (MKV, M4V ou MP4)
et prend le nouveau nom commun. Si plusieurs sorties distinctes de la file
aboutiraient au même chemin, l’opération est refusée. Les accents, espaces,
apostrophes, deux-points et esperluettes sont acceptés sans interprétation shell.
Les noms vides, chemins et caractères de contrôle sont refusés.

Les sources de montage restent à leur emplacement. Leurs références absolues
restent identiques ; les références relatives sont figées dans le référentiel
du processus, conformément aux lecteurs actuels. Les bornes et la sélection des
pistes ne sont pas modifiées. Aucun remplacement global des chaînes du JSON
n’est effectué.

Toutes les tâches liées au projet reçoivent les nouveaux chemins, sans changer
leur état, leur historique ni leur nombre de tentatives. Une transaction SQLite
immédiate empêche une prise en charge concurrente pendant les vérifications.
Le worker recharge déjà la tâche après sa prise en charge : il utilise ainsi les
chemins actualisés même s’il avait consulté la file avant le déplacement.

Sur un même volume, la vidéo utilise un lien physique puis le retrait de
l’ancien chemin. Entre volumes, elle est copiée et synchronisée avant ce
retrait ; cette opération peut prendre du temps. La base n’est validée qu’une
fois les destinations créées. Une erreur avant cette validation retire ces
destinations et conserve les originaux. Après validation, un échec de suppression
d’un ancien fichier produit un avertissement plutôt que de retirer la nouvelle
copie valide. Une interruption brutale du processus peut laisser des doublons à
examiner ; ne pas forcer un écrasement pour relancer l’opération.

Les reçus gardent leurs informations d’encodage ; seuls les chemins sont
actualisés. L’empreinte du projet n’est actualisée que si elle correspondait
effectivement au projet avant le déplacement. Un JSON modifié après l’encodage
n’est pas présenté artificiellement comme la recette de cet ancien export.

Cette commande actualise video_encoder ; elle n’écrit pas directement dans la
base vidb. Les chemins de vidéothèque devront être pris en compte par sa
réconciliation. Le reçu déplacé reste disponible à côté de la vidéo.

Équivalent CLI :

```sh
bin/video_encoder move-project /videos/mon_projet.json --directory /videos/autre-dossier
bin/video_encoder move-project /videos/mon_projet.json --directory /videos --name 'Nouveau nom' --preview
bin/video_encoder move-project /videos/mon_projet.json --directory /videos --name 'Nouveau nom'
```

## Quarantaine d’une source

La commande **Sources → Mettre une source en quarantaine…** est conservée : elle
vérifie l’utilisation de la capture par les tâches et demande de confirmer que
tous les montages utiles ont été réalisés. Un déplacement sous Dolphin ne fait
pas ces contrôles. La quarantaine actuelle ne réécrit pas non plus les anciens
projets : conserver la source à son emplacement si un montage doit encore être
repris, ou rétablir explicitement sa référence lors de cette reprise.
La quarantaine d’une capture ne remplace pas le déplacement d’un projet et de
sa vidéo ; aucune suppression automatique des captures n’est ajoutée.
