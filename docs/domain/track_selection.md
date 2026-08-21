# Sélection des pistes

## Objectif

Le sélecteur de pistes détermine les pistes utiles à conserver pour l’encodage d’un média.

Il ne cherche pas à reproduire toutes les pistes déclarées dans le multiplex. Il applique une politique de sélection afin de conserver une version française, une éventuelle version originale et les sous-titres nécessaires à cette dernière.

La sélection repose uniquement sur les métadonnées observées. Elle ne vérifie pas si une piste contient effectivement un flux exploitable.

## Niveaux de connaissance

La sélection distingue trois niveaux.

### Métadonnées observées

Les métadonnées sont produites par l’analyse du média.

Une piste peut notamment être décrite par :

- son type ;
- son index ;
- son codec ;
- sa langue déclarée ;
- son statut par défaut ;
- son statut forcé ;
- ses indicateurs d’accessibilité.

Ces informations décrivent ce qui est annoncé dans le multiplex.

### Interprétation

Certaines métadonnées doivent être interprétées selon les conventions observées chez les diffuseurs.

Par exemple :

- `fra` ou `fre` désigne une piste française ;
- `qaa` ne désigne pas une langue ;
- `qaa` indique le rôle de version originale ;
- `visual_impaired` signale une piste destinée aux personnes déficientes visuelles ;
- `hearing_impaired` signale une piste destinée aux personnes sourdes ou malentendantes.

L’interprétation ne constitue pas encore une décision de sélection.

### Politique de sélection

La politique détermine les pistes conservées pour l’encodage.

Elle utilise les rôles interprétés à partir des métadonnées, mais reste distincte de cette interprétation.

## Convention `qaa`

La valeur `qaa` est utilisée par plusieurs diffuseurs pour identifier la piste jouant le rôle de version originale.

Elle ne représente pas la langue réelle du contenu.

Selon l’œuvre diffusée, la piste `qaa` peut contenir notamment de l’anglais, de l’italien, du suédois,
de l’allemand, du français.

La présence d’une piste `qaa` signifie donc :

> une piste est déclarée comme version originale.

Elle ne garantit pas :

- que cette piste soit dans une langue étrangère ;
- que son contenu soit différent de la piste française ;
- que son flux soit effectivement exploitable.

## Pistes audio

### Version française

La première piste audio dont la langue déclarée est `fra` ou `fre` est considérée comme la version française.

Elle est conservée lorsqu’elle n’est pas marquée comme piste d’accessibilité.

### Version originale

La première piste audio dont la langue déclarée est `qaa` est considérée comme la version originale.

Elle est conservée lorsqu’elle n’est pas marquée comme piste d’accessibilité.

Une piste audio ne doit pas être considérée comme originale uniquement parce que sa langue n’est pas française.

Une piste `deu`, `eng` ou `ita`, par exemple, n’est pas automatiquement une version originale.

### Accessibilité

Les pistes audio marquées `visual_impaired` ne sont pas conservées dans la sélection audio ordinaire.

Les indicateurs d’accessibilité sont distincts de la langue et du rôle de la piste.

Une piste `qaa` et une piste d’accessibilité doivent donc être représentées par des pistes distinctes lorsqu’elles correspondent à des fonctions différentes dans le multiplex.

### Pistes étrangères supplémentaires

Une piste dans une autre langue que le français n’est pas conservée simplement parce qu’elle est étrangère.

Lorsqu’un média contient par exemple :

- une piste française ;
- une piste `qaa` ;
- une piste allemande supplémentaire ;

la sélection conserve :

- la piste française ;
- la piste `qaa`.

La piste allemande supplémentaire n’est pas sélectionnée.

Cette règle couvre notamment les multiplex comportant plusieurs versions linguistiques, sans introduire pour l’instant de traitement particulier par diffuseur.

### Absence de version originale

Lorsqu’un média possède une piste française mais aucune piste `qaa`, il est interprété comme une simple version française.

La sélection conserve uniquement la piste française.

L’absence de `qaa` signifie que le multiplex ne déclare aucune version originale distincte.

## Sous-titres

### Sous-titres français ordinaires

Les sous-titres français ordinaires sont conservés lorsqu’une piste audio de version originale est sélectionnée.

Ils permettent d’accompagner la lecture de la version originale.

Les observations actuelles montrent qu'il n'existe généralement qu'une seule piste de sous-titres français ordinaire. La sélection retourne néanmoins une collection afin de ne pas imposer cette hypothèse au modèle.

### Sous-titres pour sourds et malentendants

Les pistes de sous-titres marquées `hearing_impaired` ne sont pas conservées dans la sélection ordinaire.

### Absence de version originale

Lorsqu’aucune piste `qaa` n’est disponible, aucun sous-titre n’est sélectionné.

Même si des pistes de sous-titres français sont déclarées dans le multiplex, elles ne sont pas considérées comme nécessaires à une simple version française.

## Piste vidéo

La première piste vidéo déclarée est sélectionnée.

Aucune autre politique de choix vidéo n’est définie pour le moment.

## Règles actuelles

La politique actuelle peut être résumée ainsi :

| Situation                                      | Audio sélectionné | Sous-titres sélectionnés |
| ---------------------------------------------- | ----------------- | ------------------------ |
| Version française seule                        | Français          | Aucun                    |
| Français et version originale                  | Français et `qaa` | Français ordinaires      |
| Français, accessibilité et version originale   | Français et `qaa` | Français ordinaires      |
| Français, version originale et autre langue    | Français et `qaa` | Français ordinaires      |
| Français sans `qaa`, avec sous-titres déclarés | Français          | Aucun                    |

## Montage multi-source

### Pistes sources et pistes de sortie

Dans un montage multi-source, une piste présente dans un média ne correspond pas directement à une piste du fichier exporté.

Une piste de sortie est assemblée à partir d'une piste sélectionnée dans chaque média utilisé par le montage.

Par exemple :

| Rôle de sortie    | Média A                   | Média C                   |
| ----------------- | ------------------------- | ------------------------- |
| Français          | piste `fra` ou `fre` de A | piste `fra` ou `fre` de C |
| Version originale | piste `qaa` de A          | piste `qaa` de C          |

`Track` représente une piste observée dans un média.

`AudioOutputTrack` représente une piste à produire. Elle possède :

- un rôle métier, actuellement `french` ou `original` ;
- une association entre chaque média source et la piste sélectionnée dans ce média.

### Complétude d'une piste de sortie

Une piste de sortie est produite uniquement lorsqu'une piste correspondant à son rôle est disponible dans chaque média utilisé par le montage.

Si tous les médias possèdent une piste française sélectionnable, la piste française de sortie est produite.

Si au moins un média ne possède aucune piste `qaa`, la piste de version originale est entièrement omise.

Aucun silence n'est inséré et aucune autre piste étrangère n'est utilisée comme remplacement.

En particulier, une piste `deu`, `eng` ou `ita` ne remplace pas une piste `qaa` absente.

### Sous-titres

Les sous-titres associés à la version originale sont produits uniquement lorsqu'une piste de sortie originale complète est disponible.

Lorsque la version originale est omise, les sous-titres qui lui sont associés sont également omis.

### Métadonnées du fichier exporté

La piste française produite reçoit la métadonnée :

```text
language=fra
```

La piste de version originale produite reçoit la métadonnée :

```
language=qaa
```

La valeur `qaa` est conservée afin que le fichier exporté puisse être utilisé comme  source d'un montage ultérieur et que son rôle de version originale reste identifiable.

Elle ne prétend pas représenter la langue réelle du contenu.

### Construction de l'export

Chaque piste audio de sortie est rendue à partir d'un projet MLT distinct.

Pour une même piste de sortie,  chaque média peut utiliser un index de flux différent. La sélection est  donc effectuée par média source et non à partir d'un index audio global.

## Limites connues

### Langue réelle de la version originale

Le modèle actuel conserve `qaa` dans la propriété `language`.

Il ne représente pas séparément le rôle de version originale ou la langue réelle du contenu de cette piste.

Il n’est donc pas possible de déterminer, avec les seules données actuelles, si une piste `qaa` contient de l’anglais, du français, de l’allemand ou une autre langue.

### Pistes déclarées mais inactives

Une piste peut être présente dans les métadonnées tout en ne produisant aucun contenu exploitable.

Le sélecteur travaille sur les pistes déclarées et ne cherche pas à détecter :

- les pistes silencieuses ;
- les pistes vides ;
- les pistes intermittentes ;
- les flux qui ne produisent aucune sortie lors de l’encodage.

Cette détection appartient à une éventuelle étape ultérieure d’analyse ou de validation.

### Duplication entre `fra` et `qaa`

Certains multiplex déclarent simultanément :

- une piste `fra` ;
- une piste `qaa` contenant également du français.

Le modèle actuel ne permet pas de déterminer s’il s’agit :

- d’une véritable version originale française ;
- d’une duplication technique ;
- d’une piste inactive.

La politique conserve donc les deux pistes tant que la piste `qaa` est déclarée comme version originale et qu’aucune information supplémentaire ne permet de l’écarter.

### Conventions propres aux diffuseurs

Les observations montrent que certains diffuseurs peuvent ajouter des pistes particulières.

ARTE diffuse fréquemment :

- une version française ;
- une version originale `qaa` ;
- une version allemande `deu`.

La politique actuelle ne conserve pas automatiquement la piste allemande supplémentaire.

Aucune stratégie propre à un diffuseur n’est introduite tant que plusieurs règles spécifiques et durables ne justifient pas cette abstraction.

## Principes de conception

### Séparer les faits de leur interprétation

Une valeur observée ne doit pas être confondue avec sa signification métier.

Par exemple :

- fait observé : `language == "qaa"` ;
- interprétation : la piste joue le rôle de version originale ;
- décision : conserver cette piste.

### Ne pas déduire la version originale par exclusion

La version originale ne doit pas être définie comme la première piste qui n’est pas française.

Elle doit être identifiée à partir d’une convention explicitement reconnue.

### Ne pas enrichir le modèle prématurément

Les concepts de langue, de rôle et d’accessibilité sont actuellement interprétés par `TrackSelector`.

Ils pourront être déplacés ou représentés par de nouveaux objets si leur utilisation s’étend dans le domaine.

Une telle évolution devra être motivée par les besoins observés et par les tests, plutôt que par une anticipation abstraite.

### Documenter les limites

Lorsqu’une information ne peut pas être déduite avec fiabilité, le modèle ne doit pas prétendre la connaître.

Les cas ambigus doivent rester explicitement documentés jusqu’à ce que de nouvelles observations ou de nouvelles métadonnées permettent de les distinguer.