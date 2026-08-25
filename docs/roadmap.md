# Roadmap

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
- exécution du conteneur sans réseau et avec un montage limité au workspace ;
- possibilité de sélectionner une autre image pour les comparaisons et les
  retours arrière ;
- tests automatisés du lanceur sans dépendre d’un démon Docker ;
- validation du résultat OCR entre les versions 0.96.5 et 0.96.6 ;
- validation par visionnage d’un export multi-source complet.

L’image utilisée par défaut est :

```text
video-encoder-ccextractor:0.96.6-ocr-fra
```

La version 0.96.5 reste disponible comme point de comparaison et solution de
 retour arrière.

## Évolutions possibles

Les évolutions suivantes pourront être étudiées lorsqu’un besoin concret les
 justifiera :

- vérifier explicitement la disponibilité de Docker et de l’image configurée
   avant le démarrage d’un export ;
- publier les images dans un registre si `video_encoder` doit être installé sur
   une autre machine ;
- automatiser une partie de la construction et des tests d’acceptation des
   nouvelles versions ;
- définir une politique de conservation et de suppression des anciennes
   images ;
- surveiller les nouvelles versions de CCExtractor et leurs effets sur le
   décodage DVB, l’OCR et la synchronisation.
