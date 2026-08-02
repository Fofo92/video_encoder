# Carnet de laboratoire des opérations de trimming avec ffmpeg

## TRIM-001

### Question : Toutes les pistes sont-elles conservées ?

### Commande

`ffmpeg -ss 00:30:00 -to 00:31:00 -i 'The Truman Show.m2t' -map 0 -c copy output.ts`

### Observation

- Le fichier est lisible.

- Toutes les pistes audio sont présentes :

  - français,
  - français malvoyants,
  - version originale (anglais)

- Toutes les pistes de sous-titres sont présentes : 

  - sous-titres pour malentendants, en français
  - français.

- La durée est de : 00:01:00.88

- Pas de moyen de vérifier si la vidéo commence un peu avant l'instant demandé.

- Quelques erreurs rapportées par **ffmpeg** :

  ```shell
  [h264 @ 0x5629193e7840] mmco: unref short failure
      Last message repeated 1 times
  [h264 @ 0x5629193e7840] number of reference frames (0+5) exceeds max (4; probably corrupt input), discarding one
  [h264 @ 0x5629193e7840] mmco: unref short failure
      Last message repeated 1 times
  ```

### Conclusion

La copie de tous les flux avec `-map 0` permet de préserver la structure complète du multiplex.

## TRIM-002

### Question : Où commence réellement la vidéo ?

#### Test "`-ss` Before"

##### Commande A

`ffmpeg -ss 00:30:00 -to 00:31:00 -i 'The Truman Show.m2t' -map 0 -c copy before.ts`

##### Observation

- Le fichier est lisible.

- Toutes les pistes audio sont présentes :

  - français,
  - français malvoyants,
  - version originale (anglais)

- Toutes les pistes de sous-titres sont présentes : 

  - sous-titres pour malentendants, en français
  - français.

- La durée est de : 00:01:00.88

- Des erreurs rapportées par **ffmpeg** en nombre plus important dont  :

  ```shell
  [h264 @ 0x55d75a522b00] decode_slice_header error
  [h264 @ 0x55d75a522b00] no frame!
  [h264 @ 0x55d75a522b00] non-existing PPS 0 referenced
  
  [...]
  
  [h264 @ 0x5629193e7840] mmco: unref short failure
      Last message repeated 1 times
  [h264 @ 0x5629193e7840] number of reference frames (0+5) exceeds max (4; probably corrupt input), discarding one
  [h264 @ 0x5629193e7840] mmco: unref short failure
      Last message repeated 1 times
  ```

#### Test "`-ss` after"

##### Commande B

`ffmpeg -i 'The Truman Show.m2t' -ss 00:30:00 -to 00:31:00 -map 0 -c copy after.ts`

##### Observation

- Le fichier est lisible.

- Toutes les pistes audio sont présentes :

  - français,
  - français malvoyants,
  - version originale (anglais)

- Toutes les pistes de sous-titres sont présentes : 

  - sous-titres pour malentendants, en français
  - français.

- La durée est de : 00:01:00.08

- Mêmes erreurs rapportées par **ffmpeg** que pour TRIM-001 :

  ```shell
  [h264 @ 0x5629193e7840] mmco: unref short failure
      Last message repeated 1 times
  [h264 @ 0x5629193e7840] number of reference frames (0+5) exceeds max (4; probably corrupt input), discarding one
  [h264 @ 0x5629193e7840] mmco: unref short failure
      Last message repeated 1 times
  ```

#### Observations comparatives

- Les tailles de fichier TRIM-001 et "-ss before" sont identiques (31 Mo)

- La taille du fichier "-ss after" est légèrement inférieure (30,6 Mo) aux précédents

- Les fichiers  de "-ss before" et "-ss after" commencent au même endroit, légèrement après le fichier de TRIM-001

- La différence de durée est quasi nulle : 00:00:00.80

#### Conclusion

- Avec `-c copy`, placer `-ss` après `-i` produit ici une durée plus proche de la durée demandée, un fichier légèrement plus petit et moins d’erreurs H.264 au démarrage. Les flux sont conservés dans les deux cas.

## TRIM-003

### Objet : Mesurer réellement le point de coupe

#### Test "`-ss` before_seek"

##### Commande A

`ffmpeg -ss 00:14:45 -i 'The Truman Show.m2t' -map 0 -c copy -t 00:00:10 before_seek.ts`

##### Observations

- La première image visible se situe quelques secondes avant l'image de changement de scène,
- L'image semble correcte tout de suite,
- Le fichier est de 5.4 Mo,
- La synchronisation audio ne semble pas mise en défaut,
- Pas d'écran noir ni d'artefact visible.

#### Test "-ss after_seek"

##### Commande B

`ffmpeg -i 'The Truman Show.m2t' -ss 00:14:45  -map 0 -c copy -t 00:00:10 after_seek.ts`

##### Observations

- La première image visible se situe quelques secondes avant l'image de changement de scène,
- L'image semble correcte tout de suite,
- Le fichier est de 4.5 Mo, donc l'extrait est légèrement plus court
- La synchronisation audio ne semble pas mise en défaut,
- Pas d'écran noir ni d'artefact visible.

#### Conclusion

Sur le fichier testé, le placement de `-ss` avant ou après `-i` produit une vidéo immédiatement exploitable, sans artefact visible ni défaut de synchronisation. La position de `-ss` modifie cependant le contenu exact et la taille de l’extrait.

## TRIM-004

### Objet : Comparer objectivement les débuts

#### Observation

- Dans les trois enregistrements les premiers mots sont identiques.

#### Conclusion

Les deux approches sont fonctionnellement équivalentes sur ce type d'enregistrement, mais `-ss after` produit des fichiers légèrement plus propres d'un point de vue technique.

## Conclusion provisoire (TRIM-001 à 004)

Avec les expériences TRIM-001 à 004, la commande **ffmpeg** qui semble la plus adaptées est vraisemblablement :

`ffmpeg -i input.ts -ss START -t DURATION -map 0 -c copy output.ts`

En effet, ces observations montrent qu'elle présente plusieurs petits avantages, sans inconvénient visible.TRIM-003

## TRIM-005

### Objet : Extraire deux segments puis les concaténer sans ré-encodage

#### Commandes

Prendre deux portions courtes et nettement séparées du même fichier, par exemple :

`ffmpeg -i 'The Truman Show.m2t' -ss 01:02:40 -map 0 -c copy -t 00:01:00 segment_1.ts`

et :

`ffmpeg -i 'The Truman Show.m2t' -ss 01:09:55.07 -map 0 -c copy -t 00:01:00 segment_2.ts`

Créer ensuite un fichier `segments.txt` avec le contenu suivant :

```txt
file 'segment_1.ts'
file 'segment_2.ts'
```

Concaténer : 

`ffmpeg -f concat -safe 0 -i segments.txt -map 0 -c copy joined.ts`

Vérifier avec la commande : `ffprobe -hide_banner joined.ts`

#### Observations

- le fichier final est lisible immédiatement,
- la durée est  de 00:02:00.33, pour une durée demandée de 2 minutes,
- toutes les pistes audio et de sous-titres sont présentes et  lisibles
- le passage entre les deux segments vidéo est perceptible, la dernière image du segment 1 est figée un instant avant de reprendre sur le segment suivant, avec une coupure des dernières images du premier segment, et une légère instabilité dur les premières images du segment 2. 
- Le passage audio du deuxième segment débute pendant cette période de figeage de l'image. à cette nuance près, l'audio reste synchronisée avec l'image au cours du passage, notamment pour le deuxième segment (ce qui veut dire que les premières images du second segment ne sont pas affichées)
- FFmpeg signale les erreurs suivantes, dont la dernière est nouvelle, pendant la concaténation :

```
[h264 @ 0x5619871cca80] mmco: unref short failure
    Last message repeated 1 times
[h264 @ 0x5619871cca80] number of reference frames (0+5) exceeds max (4; probably corrupt input), discarding one
[h264 @ 0x5619871cca80] mmco: unref short failure
    Last message repeated 1 times
[h264 @ 0x5619871cca80] number of reference frames (0+5) exceeds max (4; probably corrupt input), discarding one
[h264 @ 0x5619871cca80] Increasing reorder buffer to 2

```

