# Chemins contenant de la ponctuation

Les chemins sont transmis en arguments distincts aux programmes externes.
Il ne faut pas ajouter d’échappement shell aux noms de fichiers eux-mêmes.

Les formats intermédiaires ont leurs propres règles :
- XML MLT : échappement XML puis restitution exacte à la lecture ;
- JSON : sérialisation et lecture JSON ;
- FFconcat : apostrophes protégées selon la syntaxe de sa liste de fichiers ;
- Docker : montage explicite avec champs CSV protégés, y compris les guillemets.

Le jeu partagé de tests `spec/fixtures/path_names.json` contient des noms avec
espaces, accents, Unicode, &, deux-points, virgules, apostrophes, guillemets,
parenthèses, crochets, < >, #, %, $, substitutions de commande littérales,
points-virgules, antislashs, tiret initial et espace final.

Les tests vérifient :
- source et limites restituées après sauvegarde/réouverture du projet ;
- passage réel par les processus de conversion et de mise en file (CLI de test) ;
- arguments reçus par un processus Ruby réel ;
- restitution des chemins à partir du XML MLT et du JSON ;
- lecture par FFmpeg réel d’une liste FFconcat produite par le code Ruby ;
- arguments Docker du lanceur OCR, avec Docker simulé.

Ces tests ne constituent pas un réencodage complet pour chaque nom : le rendu
MLT natif et l’OCR réel dans Docker ne sont pas exécutés dans cette matrice.
Les retours à la ligne et caractères de contrôle ne font pas partie des noms
pris en charge par cette vérification ; aucune garantie universelle n’est avancée.
