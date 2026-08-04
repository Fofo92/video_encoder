# Carnet de laboratoire des opérations avec melt

## MLT-001

### Question : Quel est le plus petit projet MLT permettant d'assembler deux segments ?

Créer un projet contenant deux segment collés :

```txt
The Truman Show.m2t

Segment 1 :
01:02:40 → 01:03:40

Segment 2 :
01:09:55 → 01:10:55
```

avec aucun effet, transition, fondu, titre, piste supplémentaire

### Observation

- Le projet **Kdenlive** est un fichier **xml**,

- Les segments semblent représentés par des balises `entry in` et `entry out` (audio) et `in` ou `out` (video). Je ne sais pas s'il y a aussi des balises pour les sous-titres (souvenons-nous que **Kdenlive** ne semble pas prendre en compte les sous-titres au format `dvb`, même s'il les identifie).

- Les paramètres d'encodage semblent inclus dans le fichier de projet (ratio, codec, effets ?, etc.), ou dans les descriptions de plages vidéo ou audio.

- Les paramètres d'encodage sont-ils totalement séparés de la timeline ? Il semblerait que non : ce que j'en comprends, c'est que des objets vidéo sont définis par des balises `<producer>` avec leur caractéristiques et leur timeline (balises `in` et `out`) :

  ```xml
   <producer id="producer0" in="00:00:00.000" out="00:07:00.080">
    <property name="length">2147483647</property>
    <property name="eof">continue</property>
    <property name="resource">black</property>
    <property name="aspect_ratio">1</property>
    ...
  ```

-  Les pistes audio sont identifiées par des balises `<playlist>` incluant le timeline avec les balises `entry` paramètres `in` et `out`

```xml
<playlist id="playlist6">
  <property name="kdenlive:audio_track">1</property>
  <entry in="01:02:40.000" out="01:03:40.000" producer="chain0">
   <property name="kdenlive:id">4</property>
  </entry>
  <entry in="01:09:55.000" out="01:10:55.000" producer="chain0">
   <property name="kdenlive:id">4</property>
  </entry>
 </playlist>
```

- La concaténation me semble réalisée par la juxtaposition de blocs `<entry>` au sein d'un bloc `<producer>`

## MLT-002

### Objet

Comprendre comment **MLT** représente un projet minimal composé de deux segments issus d'un même fichier.

### Observations

- Le projet **Kdenlive** est un fichier XML conforme au format **MLT**.
- Le fichier source n'est pas référencé directement dans les playlists. Il est représenté par un objet `chain`, qui encapsule le média et ses caractéristiques :

```xml
<chain id="chain0">
  <property name="resource">The Truman Show.m2t</property>
  <property name="mlt_service">avformat-novalidate</property>
  ...
</chain>
```

Les caractéristiques techniques du média (codec, résolution, nombre de flux, etc.) sont associées à cette chaîne.

Les segments sont définis dans une `playlist` par une succession de balises `entry` faisant référence à la même chaîne :

```xml
<playlist id="playlist6">
  <entry producer="chain0"
         in="01:02:40.000"
         out="01:03:40.000"/>
  <entry producer="chain0"
         in="01:09:55.000"
         out="01:10:55.000"/>
</playlist>
```

La concaténation des segments est  donc obtenue par la succession des entrées de la playlist. Une même  chaîne peut être référencée plusieurs fois avec des points d'entrée et  de sortie différents, conformément au modèle **MLT**.

Les playlists sont ensuite regroupées dans un `tractor`, qui constitue l'objet chargé d'assembler les différentes pistes (audio, vidéo, etc.) pour le rendu.

- Plusieurs `tractor` et `chain` sont présents dans le projet. Leur rôle exact reste à déterminer.

### Conclusion provisoire

Le cœur d'un projet MLT apparaît remarquablement simple :

```

Fichier source
        │
        ▼
      Chain
        │
        ▼
    Playlist
 (suite de segments)
        │
        ▼
     Tractor
        │
        ▼
      Rendu
```

La description de la *timeline* est essentiellement portée par la `playlist`, qui définit une suite ordonnée de segments au moyen des attributs `in` et `out`.

Les informations spécifiques à  **Kdenlive** (interface, organisation du projet, etc.) semblent coexister  avec les objets **melt** sans modifier ce principe fondamental.

Il reste à déterminer comment cette description est exploitée lors du rendu, et notamment quelles commandes sont transmises à **melt** et comment les paramètres d'encodage y sont associés.

## MLT-003

### Objet

Observer comment **melt** produit le fichier final.

### Commande

Encoder avec **melt** :

`melt-7 mlt-001.kdenlive -consumer avformat:test.mkv vcodec=libx265`

### Conclusion

L'expérience montre que **`melt` peut interpréter directement un projet Kdenlive**, sans passer par l'interface graphique.

Le rendu est obtenu au moyen du consumer `avformat`, auquel les paramètres d'encodage sont transmis sous la forme `option=valeur`, conformément à la documentation de MLT. La syntaxe est proche de celle de **FFmpeg**, bien que toutes les options de ce dernier ne soient pas nécessairement disponibles.

Elle a permis de produire un fichier vidéo encodé en **HEVC** à partir de la *timeline* décrite dans le projet.

Cette expérience confirme que :

- un projet **Kdenlive** constitue une entrée valide pour `melt` ;
- le consumer `avformat` permet de contrôler les paramètres d'encodage depuis la ligne de commande ;
- la description de la timeline est indépendante des paramètres d'encodage, ceux-ci pouvant être fournis lors du rendu.

De nombreux messages affichés pendant le rendu (références H.264 manquantes, avertissements MPEG-TS, changements de propriétés vidéo) n'ont pas empêché la production du fichier final. Leur origine et leur impact restent à analyser.

### Conclusion provisoire

L'architecture de **MLT** apparaît compatible avec les objectifs de **video_encoder** :

- la *timeline* est décrite indépendamment de l'encodage ;
- le rendu est assuré par `melt` ;
- les paramètres d'encodage restent maîtrisés par l'application.

Il reste toutefois à déterminer dans quelle mesure cette architecture permet de conserver plusieurs pistes audio et les sous-titres DVB, qui ne sont pas présents dans le premier rendu obtenu.

## MLT-004

### Objet

Examen visuel de la sortie

### Observation

#### 1. La jonction est propre

Le résultat le plus important est positif :

- passage précis entre les deux segments ;
- aucune image figée ;
- pas de perte visible au début du second segment ;
- synchronisation correcte.

Cela confirme que **le rendu de la *timeline* par MLT résout le défaut observé avec la concaténation brute en `-c copy`**.

#### 2. Une seule piste audio et aucun sous-titre

Le fichier contient seulement :

```

Vidéo : HEVC
Audio : Vorbis stéréo
Sous-titres : aucun
```

MLT rend donc ici les pistes présentes dans la timeline Kdenlive, pas l’ensemble des flux du multiplex source.

Il faudra déterminer comment :

- rendre plusieurs pistes audio séparément ;
- conserver leurs langues et rôles ;
- traiter les sous-titres DVB ;
- remultiplexer le tout dans le fichier final.

#### 3. La résolution a changé

C’est le point à ne pas manquer :

```

Source : 1920 × 1080
Sortie : 1280 × 720
```

Le projet **Kdenlive** impose vraisemblablement un **profil 720p** à la timeline. MLT ne se contente donc pas de juxtaposer les segments : il normalise aussi la vidéo selon le profil du projet.

Avant toute intégration, nous devrons explicitement fixer :

```
1920 × 1080
25 images/s
entrelacement ou désentrelacement
espace colorimétrique BT.709
format de pixels
```

#### 4. L’audio et la vidéo n’ont pas exactement la même durée

```
Vidéo : 120,083 s
Audio : 120,028 s
Écart : 55 ms
```

Cet écart est faible et probablement imperceptible, mais il doit être noté. Sur un film complet comportant plusieurs coupes, il faudra vérifier qu’il ne s’accumule pas.

### Conclusion provisoire

> MLT rend directement la *timeline* composée de plusieurs segments avec des jonctions visuellement propres et précises. En revanche, le projet testé ne produit qu’une piste audio, ne conserve aucun sous-titre DVB et applique le profil vidéo du projet Kdenlive, ici 1280 × 720. MLT paraît donc adapté à la construction et au rendu de la *timeline*, mais la gestion des multiples pistes et du profil de sortie devra être explicitement étudiée.

## MLT-005

### Question

Vérifier qu’un profil MLT adapté à la TNT HD française permet de conserver la résolution et les caractéristiques vidéo de la source.

### Commande

```
melt-7 \
  -profile atsc_1080i_50 \
  mlt-001.kdenlive \
  -consumer avformat:test-1080i.mkv \
  vcodec=libx265
```

### Observations :

Le fichier produit présente les caractéristiques suivantes :

- vidéo HEVC ;
- résolution `1920 × 1080` ;
- cadence de `25 images par seconde` ;
- format d’image `16:9` ;
- espace colorimétrique BT.709 ;
- durée vidéo de `00:02:00.083` ;
- une seule piste audio, encodée en Vorbis ;
- aucun sous-titre.

La jonction entre les deux segments est visuellement propre.

#### Conclusion

Le profil standard MLT `atsc_1080i_50` correspond aux caractéristiques générales des enregistrements TNT HD français observés :

- `1920 × 1080` ;
- `25 images par seconde` ;
- vidéo entrelacée ;
- pixels carrés ;
- format `16:9` ;
- espace colorimétrique BT.709.

Son utilisation empêche le redimensionnement involontaire en `1280 × 720` provoqué par le profil initial du projet **Kdenlive**.

## MLT-006

### Objet

Déterminer si le producteur MLT `avformat` peut exposer simultanément plusieurs pistes audio distinctes d’un même média.

### Observations

Le producteur `avformat` fournit deux propriétés de sélection audio :

- `audio_index`, qui sélectionne une piste par son index absolu ;
- `astream`, qui sélectionne une piste par son index relatif parmi les pistes audio.

La propriété `astream` est prioritaire sur `audio_index`.

Dans les deux cas, une seule piste audio est sélectionnée par défaut.

La valeur spéciale `all` permet de prendre en compte toutes les pistes audio, mais celles-ci sont regroupées sous la forme d’un ensemble de canaux dans une seule piste audio.

Ainsi, deux pistes stéréo ne sont pas conservées comme deux pistes indépendantes : elles deviennent potentiellement une seule piste multicanale.

Le projet Kdenlive observé utilise :

```xml
<property name="audio_index">1</property>
<property name="astream">0</property>
```

Il sélectionne donc la première piste audio relative du média.

### Conclusion

Le producteur MLT `avformat` ne paraît pas pouvoir exposer directement plusieurs pistes audio indépendantes au moyen d’un seul `chain`.

La valeur `all` ne répond pas au besoin de `video_encoder`, puisqu’elle regroupe les pistes en canaux au lieu de préserver leur indépendance.

Pour conserver une VF et une VO comme deux pistes distinctes, il faudra probablement :

- créer une source ou un rendu audio distinct pour chaque piste sélectionnée ;
- appliquer à chacune la même timeline de découpage ;
- remultiplexer ensuite la vidéo, les pistes audio et les sous-titres avec FFmpeg.

MLT resterait chargé de produire des jonctions temporelles propres, tandis que FFmpeg assurerait l’assemblage final des flux indépendants.

## MLT-007

## MLT-008

### Objet

Vérifier qu’un projet MLT minimal produit par `MltProjectBuilder` permet de rendre correctement plusieurs segments d’un même enregistrement.

### Commande

```bash
melt-7 generated.mlt \
  -consumer avformat:generated-test.mkv \
  vcodec=libx265
```

### Observations

* Le fichier Matroska produit est lisible.
* La vidéo paraît propre.
* La jonction entre les deux segments est nette.
* La précision de la coupe à l’image près reste à confirmer.
* Une seule piste audio est produite.
* Aucun sous-titre n’est conservé.

### Conclusion

Le document MLT minimal engendré par `MltProjectBuilder` suffit à décrire et rendre une timeline composée de plusieurs segments.

Les informations supplémentaires présentes dans un projet Kdenlive ne sont donc pas nécessaires au besoin actuel de `video_encoder`.

MLT est validé comme moteur de *timeline* pour obtenir des jonctions propres. La gestion des pistes audio multiples et des sous-titres devra être réalisée séparément.

## La suite logique

Je ne chercherais pas encore la précision à l’image près. Nous savons déjà que MLT produit une jonction nettement meilleure que la concaténation FFmpeg en copie de flux.

Le prochain chantier devrait être la **séparation des rendus par flux** :

```text
timeline unique
    ├── vidéo
    ├── audio VF
    └── audio VO

puis leur remultiplexage par FFmpeg.
### Conclusion Générale

MLT semble être un candidat crédible pour réaliser le découpage et la reconstitution du film. En effet :

- une timeline est représentée de manière simple et cohérente ;
- `melt` peut être piloté en ligne de commande ;
- l'encodage est configurable ;
- la qualité des jonctions est bien meilleure que celle obtenue par une simple concaténation de flux.

Il reste encore quelques inconnues importantes :

- la gestion des multiples pistes audio ;
- les sous-titres DVB ;
- les paramètres exacts du consumer `avformat`.
