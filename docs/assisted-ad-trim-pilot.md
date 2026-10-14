# Propositions de coupures publicitaires : pilote 6ter

Le pilote transforme un rapport `video_encoder.6ter_boundary_hypotheses` version 3
en projet de montage version 2, ouvrable dans l'éditeur existant. Il ne lance
aucun export et n'utilise pas les segments du montage de référence.

```bash
ruby script/propose_ad_trim.rb \
  --report /tmp/analyse/boundary-hypotheses.json \
  --output /tmp/proposition-a-revoir.json
bin/video_encoder_ui /tmp/proposition-a-revoir.json
```

Le fichier `window-cache.json` doit se trouver à côté du rapport. La source doit
toujours avoir le même chemin, la même taille et la même date de modification.
Le générateur refuse d'écraser un fichier existant. Il vérifie la cadence moyenne
de 25 images/s utilisée pour ce pilote. Il refuse les coupures hors limites,
chevauchantes, non ordonnées ou incompatibles avec leurs candidats.

Par défaut, seuls les intervalles publicitaires appariés sont retirés. Le début
et la fin de la capture sont conservés. Les candidats non appariés sont conservés
également : ils peuvent se trouver dans les marges, hors de l'épisode ciblé.

## Revue du montage

Le parcours conseillé commence maintenant dans l'éditeur, sur la capture :

1. Poser **IN** au début de l'épisode, puis **OUT** à sa fin, générique compris
   si l'on souhaite le conserver.
2. Cliquer sur **Créer avec coupures…** et sélectionner le fichier
   `boundary-hypotheses.json` issu de l'analyse de cette capture.
3. Le montage est créé uniquement dans cette plage. Il remplace les segments
   en mémoire et devient un nouveau projet à enregistrer ; aucun projet
   existant n'est écrit. Vérifier les raccords, puis sauvegarder et exporter.

La génération s'exécute en arrière-plan. Les actions qui modifieraient le
montage sont temporairement désactivées. Une erreur laisse le montage et les
repères IN/OUT précédents intacts. Un rapport concernant une autre source est
refusé. Fermer l'éditeur interrompt la génération temporaire.

Le parcours suivant reste disponible pour ajuster une proposition déjà chargée :

1. Sélectionner le premier segment, puis choisir **Modifier IN**.
2. Ajuster sa borne avec Ctrl+← / Ctrl+→ ou les boutons −1 / +1.
3. Cliquer sur **Appliquer**, ou appuyer sur Entrée. Le segment est remplacé
   à sa place, sans changer l'ordre des autres segments.
4. Régler de même la fin du dernier segment. Examiner chaque raccord proposé.
5. Enregistrer le projet après revue, puis utiliser le parcours d'export existant.

Pendant une modification, le bouton d'ajout indique **Appliquer**. Choisir un
autre segment abandonne les ajustements
non appliqués du précédent. Si le segment ciblé a été supprimé ou déplacé avant
l'application, l'opération est refusée : le re-sélectionner et choisir Modifier IN ou OUT.

Les options `--start-frame` et `--end-frame` permettent aussi de fournir des bornes
manuelles à la génération. Les bornes sont inclusives. Le complément des coupures
est calculé dans cette plage ; les fragments d'une seule image sont refusés, car
l'éditeur actuel exige au moins deux images par segment.

### Ajustements à l'image près

Sélectionner un segment et choisir **Modifier IN** ou **Modifier OUT** dans le
sélecteur de mode : l'aperçu se place sur cette borne. Utiliser **Ctrl+← / Ctrl+→**
ou les boutons **−1 / +1** pour déplacer le repère d'une image. Cliquer sur
**Appliquer** (ou Entrée) pour remplacer le segment à sa place.

Les flèches simples conservent leur navigation habituelle. Les décalages sont
refusés pendant un export ou une génération de proposition, en dehors de la
source, ou lorsqu'ils laisseraient moins de deux images dans le segment.

Avec le script autonome, le fichier `.review.json` accompagne la proposition initiale : signature de la
source, empreinte du rapport, coupures et quantité d'images conservées. Il n'est
pas mis à jour lors des sauvegardes dans l'éditeur et ne constitue pas un reçu
d'export ni une validation du montage.

Dans le parcours intégré à l'éditeur, les fichiers intermédiaires sont
temporaires ; seul le montage en mémoire est conservé, puis enregistré via
le parcours normal de l'éditeur.

## Limites du pilote

Le détecteur et l'affinage 6ter restent des scripts expérimentaux externes.
Les huit pauses de quatre captures 9-1-1 ont été retrouvées après calibration sur
ce corpus ; ce résultat ne mesure pas la fiabilité sur d'autres captures.
La détection générale du début et de la fin d'une œuvre reste hors de ce pilote.
La proposition demeure à examiner avant export.

## Navigation directe aux bornes

Deux boutons remplacent le menu « Aller à ». Avec un segment sélectionné,
ils affichent IN et OUT et déplacent la lecture vers ses bornes enregistrées.
Sans sélection, ils affichent Début source et Fin source, avec les icônes de
début/fin. Ils ne posent ni ne modifient de balise et sont désactivés pendant
une opération en arrière-plan. Le mode Modifier IN/OUT reste distinct.

## Suite : analyse et sélection du rapport intégrées

Faire de Créer avec coupures un parcours intégré : chercher un rapport valide
pour la capture et sa signature (chemin, taille, date de modification), en
privilégiant une révision corrigée. Sans rapport exploitable, lancer la
détection puis l'affinage de façon asynchrone, avec progression et annulation.
Conserver les résultats et caches sous le dossier sauvegardé du pilote, puis
appliquer les coupures dans l'enveloppe IN/OUT choisie par l'utilisateur.
Garder un choix manuel de rapport en secours. Ne pas lancer d'export avant
la revue du montage. Cette automatisation n'est pas encore implémentée.

## Suite : proposition automatique de la fin

Étudier le générique textuel comme signal de fin, même lorsqu'il est bref.
Combiner la présence de texte avec la continuité temporelle, les transitions
visuelles et le contexte après le dernier segment de programme. Les textes
publicitaires, bandes-annonces et incrustations empêchent d'en faire une règle
unique. Proposer une limite avec son contexte pour revue et conserver la
possibilité de régler OUT manuellement. Cette piste remplace l'exploitation du
motif rouge propre à 9-1-1 ; elle n'est pas implémentée dans ce pilote.

## Vérifications

```bash
ruby -c script/propose_ad_trim.rb
ruby test/propose_ad_trim_test.rb
PYTHONPATH=ui QT_QPA_PLATFORM=offscreen python3 -m unittest discover \
  -s ui/tests -p 'test_*segment*.py'
PYTHONPATH=ui python3 -m unittest discover -s ui/tests -p 'test_trim_session*.py'
```
