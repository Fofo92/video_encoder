# Destination des épisodes et sous-dossiers

Un épisode identifié propose `Sxx Exx - titre français (titre original).mkv`.
La convention existante répète un titre original identique pour une œuvre
étrangère. Le choix manuel conserve ce nom proposé.

Un dossier de série et de saison unique déjà présent reste prioritaire. Si la
série est reconnue mais sa saison absente, le chemin proposé inclut `Saison NN`.
Sans dossier de série unique, une proposition initialement à la racine `/videos`
est placée dans `/videos/Séries TV`. Aucun dossier de série arbitraire n'est créé
en présence de plusieurs correspondances. Un répertoire explicitement choisi
est conservé.

La fenêtre de destination présente un champ de chemin complet et un bouton
Parcourir. Les `/` saisis séparent les sous-dossiers ; la validation crée les
parents manquants, puis le flux habituel enregistre le projet JSON adjacent à
la future vidéo. Annuler ne crée rien. Une erreur de création est affichée.
Les vidéos existantes, les autres projets et les chemins traversant un fichier
restent refusés. Le projet chargé peut être enregistré à son emplacement actuel.
