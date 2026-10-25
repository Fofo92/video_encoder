# Premier parcours de montage multi-source

Le moteur d’export sait assembler les segments de plusieurs fichiers. L’éditeur
permet maintenant de les préparer dans un seul projet, sans modifier les sources.

1. Ouvrir la première source et ajouter une plage IN/OUT.
2. Dans **Sources → Ajouter une source au montage…** (`Ctrl+Maj+O`), choisir la
   seconde capture. Le sélecteur **Source affichée** permet de passer entre les
   fichiers ; la position de lecture de chaque source est conservée en mémoire.
3. Ajouter les plages de la seconde source. Les segments s’ajoutent à la fin du
   montage ; la colonne Source indique le nom du fichier, son chemin en infobulle.
4. Sélectionner un segment puis utiliser **Montage → Monter/Descendre le segment
   sélectionné** (`Alt+↑` / `Alt+↓`) pour changer l’ordre d’assemblage. Cliquer sur
   un segment ouvre la bonne source et positionne l’aperçu sur son début.
5. Enregistrer puis encoder ou ajouter à la file comme pour un montage ordinaire.
   Les contrôles audio existants portent sur le montage complet. Le projet reste
   ouvrable avec toutes ses sources et les bornes de chaque segment.

Le premier parcours accepte uniquement des sources ayant la même cadence exacte
(par exemple 25 et 25 images/s ; 25 et 30 sont refusées). Les plages successives
d’une même source respectent les restrictions du moteur : ordre chronologique,
sans chevauchement ni contiguïté. Un réordonnancement invalide est refusé sans
modifier la timeline. Le sélecteur et les commandes d’édition sont bloqués pendant
le contrôle audio, sa confirmation et l’encodage.

Changer de source réinitialise les repères IN/OUT affichés après confirmation si
nécessaire ; les segments ajoutés restent conservés. Une source manquante ou non
ouvrable ne remplace pas l’aperçu courant. Ajouter un fichier déjà présent active
sa référence existante au lieu de la dupliquer.

## Premier essai réel sur Zeus

Utiliser deux captures du même programme ou deux sources destinées à une même
œuvre, avec une cadence identique. Monter d’abord 10 à 20 secondes de chacune,
puis produire un fichier de test dans `/tmp` (la fiche vidb n’a pas à être créée
pour cet essai). Vérifier l’ordre des images et le raccord audio. Fermer puis
rouvrir le projet permet de contrôler que les sources et les bornes sont bien
conservées. Les sources restent en place pendant cet essai.

La mise en quarantaine reste soumise au protocole de confirmation par source :
la fin d’un montage ne signifie pas qu’il ne reste aucun autre programme utile
dans les captures. Aucun déplacement automatique supplémentaire n’est introduit.
