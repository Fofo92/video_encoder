# Roadmap

## Priorité urgente : efficacité de la détection publicitaire

Le pilote intégré repose encore sur des références 6ter. Il ne constitue pas
un détecteur généraliste ; les améliorations du parcours ne changent pas cette
limite. La capture NOVO19 de Braveheart a donné zéro candidat malgré deux
coupures repérées manuellement.

Avant les prochains travaux d'interface ou de file, évaluer Comskip sur cette
capture, puis sur d'autres chaînes : bornes retrouvées, temps de calcul et
contenu de programme proposé à tort à la suppression. L'adaptateur et son
[protocole d'essai](comskip-evaluation.md) sont disponibles ; leur validation
technique ne démontre pas encore la fiabilité sur les captures réelles.
L'intégration dans l'éditeur dépend de ces mesures. La file d'analyse séparée
viendra ensuite, sans relancer une analyse déjà terminée et inchangée.

## Parcours utilisateur et intégration avec vidb — 18 octobre 2026

Ordre convenu pour les prochaines évolutions :

1. Une seule saisie du nom et du dossier pour le projet de découpage JSON et le
   MKV ; modification possible après annulation du récapitulatif et avant le
   lancement de la tâche. Le fonctionnement est détaillé dans
   [Bornes, tâches et destinations](editor-and-queue-actions.md).
2. Finaliser le parcours d'analyse publicitaire : nettoyage des intermédiaires
   associés dès l'enregistrement du projet, emplacement automatique des
   intermédiaires, analyse et proposition clairement distinguées du chargement
   d'un rapport existant, raccords faciles à vérifier et résultats utiles
   conservés avec le projet sous le même nom de base.
3. Déplacer ou renommer les fichiers d'un projet terminé et mettre à jour leurs
   références sans réencoder.
4. Consulter vidb pour identifier l'œuvre à partir de candidats documentés et
   proposer son nom et son classement sur disque ; transmettre le résultat
   d'encodage pour compléter la fiche et rattacher sa copie.
5. Préparer, lancer et suivre les encodages depuis vidb, en réutilisant la file
   technique de video_encoder et en conservant son fonctionnement autonome.

La correction de fraîcheur et les améliorations de lecture du guide TV ont été
validées séparément dans vidb (PR n° 14). Les chantiers ci-dessus n'exigent pas
de modifier à nouveau le guide TV. Les validations seront regroupées par
parcours cohérent, avec distinction entre contrôles automatiques et usage réel.

## Distribution Docker de CCExtractor

La distribution reproductible de CCExtractor avec OCR français est
opérationnelle.

Les éléments suivants sont réalisés :

- construction des versions 0.96.5 et 0.96.6 depuis des tags et des commits
  explicitement vérifiés ;
- utilisation de l’image OCR officielle de CCExtractor comme base de
  construction ;
- ajout explicite du modèle linguistique français de Tesseract ;
- correction du numéro de version déclaré par le tag 0.96.6 ;
- production d’images Docker versionnées ;
- fourniture d’un lanceur compatible avec `CCEXTRACTOR_EXECUTABLE` ;
- exécution du conteneur sans réseau, sans téléchargement implicite d’image et
  avec un montage limité au workspace ;
- vérification de Docker et de l’image configurée avant toute création de média
  ou de workspace ;
- possibilité de sélectionner une autre image pour les comparaisons et les
  retours arrière ;
- tests automatisés du lanceur sans dépendre d’un démon Docker ;
- validation du résultat OCR entre les versions 0.96.5 et 0.96.6 ;
- validation par visionnage d’un export multi-source complet.

L’image utilisée par défaut est :

```text
video-encoder-ccextractor:0.96.6-ocr-fra
```

La version 0.96.5 reste disponible comme point de comparaison et solution de retour arrière.

## Évolutions possibles

Les évolutions suivantes pourront être étudiées lorsqu’un besoin concret les
 justifiera :

- publier les images dans un registre si `video_encoder` doit être installé sur
   une autre machine ;
- automatiser une partie de la construction et des tests d’acceptation des
   nouvelles versions ;
- définir une politique de conservation et de suppression des anciennes
   images ;
- surveiller les nouvelles versions de CCExtractor et leurs effets sur le
   décodage DVB, l’OCR et la synchronisation.

## Fiabilisation du montage et reprise d’export

### Réalisé

- chaînes MLT distinctes par segment, sans déplacement automatique des bornes ;
- validation des deux raccords et du rendu complet sur le cas de diagnostic ;
- correction du crash CCExtractor, testée dans une image de diagnostic ;
- distinction entre absence de sous-titres et panne technique ;
- conservation des groupes de sous-titres valides avant signalement d’un
  résultat incomplet ;
- avertissements Ruby transmis à l’IHM sur un canal distinct de la progression ;
- diagnostic d’erreur complet sur disque et extrait limité dans une fenêtre
  non modale ;
- refus des écrasements et des attentes interactives pendant le remuxage ;
- fonctionnement de l’IHM lorsque le ShuttleXpress est indisponible.

### À réaliser

- promouvoir l’image OCR corrigée après les contrôles de distribution ;
- proposer une décision explicite en cas de sous-titres incomplets ;
- reprendre la finalisation sans refaire les composants déjà validés ;
- enregistrer un manifeste reliant les composants au projet, aux sources
  et aux paramètres de rendu ;
- vérifier les composants avant réutilisation et le média final avant nettoyage ;
- définir la conservation des diagnostics et la suppression contrôlée
  des workspaces ;
- ouvrir un projet JSON existant pour récupération ;
- démarrer l’IHM sans argument, choisir un enregistrement et fournir un
  lanceur KDE dans la catégorie Multimédia.

La récupération effectuée pendant le diagnostic était manuelle. Elle ne
constitue pas encore une fonction de reprise disponible dans l’IHM.
