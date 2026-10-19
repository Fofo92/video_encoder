# Découverte de séquences répétées — prototype du 19 octobre 2026

## But et périmètre

Le pilote 6ter cherchait un séparateur connu ; le logo de chaîne détecté par
Comskip est un autre objet. Sur Chien & chat (TF1), Comskip désactive ce dernier
car sa présence détectée est d'environ 1 %. L'affinement par retour du logo ne
peut donc pas aider cette capture.

Ce prototype cherche des séquences visuelles animées répétées dans des extraits,
sans connaître une chaîne, un logo, une couleur ou un texte. Il ne reconnaît pas
encore la fonction publicitaire du motif et ne crée aucun découpage.

## Reproduction

Prérequis de recherche : Python 3, NumPy, FFmpeg et FFprobe. Aucune dépendance
n'est ajoutée au parcours d'encodage. Depuis le dépôt, avec les quatre extraits
déjà fournis par Pascal :

```sh
python3 script/research/repeated_visual_sequences.py \
  tmp/chien-chat-separateurs/depart-1.mp4 \
  tmp/chien-chat-separateurs/depart-2.mp4 \
  tmp/chien-chat-separateurs/reprise-1.mp4 \
  tmp/chien-chat-separateurs/reprise-2.mp4

python3 -m unittest discover -s script/research -p 'test_*.py' -v
```

Le script lit seulement les médias et écrit son rapport JSON sur la sortie
standard. Il refuse les extraits dépassant 120 secondes : la recherche dans une
capture entière, avec une mémoire et un coût de comparaison bornés, reste à
développer. Ne pas lui fournir directement un enregistrement de deux heures.

## Méthode exploratoire

Décodage à 5 images/s, empreintes RGB de 32 × 18 pixels, comparaison de fenêtres
ordonnées de 2 secondes entre extraits. Une paire passe si l'erreur RGB moyenne
quadratique racine est au plus 15 sur l'échelle 0–255 et si chaque fenêtre a un
mouvement d'au moins 2 sur cette échelle. Les fenêtres correspondantes et les
noyaux voisins sont regroupés ; le rapport exige par défaut trois extraits
distincts. L'ordre des images est conservé. Les aplats fixes et les noirs ne
fournissent pas à eux seuls un motif animé.

Ces seuils ont été explorés sur cet échantillon ; ils ne sont pas validés sur
d'autres chaînes. Le script n'utilise ni OCR, ni modèle du jingle, ni bornes
de référence. Les extraits eux-mêmes ont néanmoins été sélectionnés autour des
bornes connues : ce protocole n'est pas une évaluation à l'aveugle sur une capture.

## Mesures sur les quatre extraits TF1

Un groupe est trouvé, avec une occurrence dans chacun des quatre extraits.
Le contrôle visuel l'identifie au séparateur animé « PUB » :

| Extrait | Noyau répétitif proposé, temps relatif à l'extrait |
| --- | --- |
| depart-1 | 11,6–14,6 s |
| depart-2 | 11,6–14,6 s |
| reprise-1 | 8,2–11,6 s |
| reprise-2 | 8,2–11,6 s |

L'erreur RGB des fenêtres appariées est de 0,851 au meilleur cas et de 7,144 en
médiane. Ce sont des distances de ressemblance, pas des probabilités de publicité.

Avec les mêmes paramètres, aucun groupe n'est proposé sur huit passages voisins
ordinaires : pour chaque extrait, les images échantillonnées dans [0,7[ et
[18,28[ secondes, soit 68 secondes au total. Ces passages ont été choisis après
visionnage et excluent les séparateurs ; ils ne mesurent pas le taux de faux
positifs sur une capture entière.

Sept tests automatisés couvrent les séquences décalées, les images fixes, les
séquences indépendantes, le support insuffisant, l'ordre temporel et les entrées
trop courtes. Une répétition de publicité est explicitement laissée sans
classification : la répétition seule ne prouve pas qu'il s'agit d'un séparateur.

## Limites et suite nécessaire

Les intervalles indiquent un noyau commun, pas des limites de coupe. Les temps
sont ceux des extraits réencodés ; les positions demandées à FFmpeg pour les
extraire ne constituent pas une preuve de correspondance à l'image près avec
les coordonnées de l'éditeur. Ne pas additionner directement ces temps pour
modifier un projet source.

Il reste à retrouver le début et la fin complets du motif, vérifier la
correspondance avec la source, distinguer les répétitions publicitaires ou de
programme, puis évaluer le procédé sur des fenêtres et captures non utilisées
pour sa conception. Le son n'est pas analysé dans cette version. Les décisions
ambiguës doivent rester des propositions à vérifier. Aucun changement n'est
apporté au bouton d'analyse ni à la file d'encodage.
