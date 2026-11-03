# Destination des films et documentaires identifiés

La proposition utilise les genres transmis par la fiche vidb sélectionnée, y compris
une fiche préexistante. Pour les films, tous les genres sont conservés, sans limite à deux genres.
Un film est proposé sous `/videos/Films/<genres>/Titre.mkv`.
Documentaire est un genre unique : il choisit directement `/videos/Documentaires`,
sans sous-dossier de genres. Même si une ancienne fiche transmet plusieurs genres
dont Documentaire, la destination reste cette racine. La fiche elle-même n’est pas modifiée.

Un dossier existant est réutilisé lorsque tous ses genres concordent, indépendamment
de leur ordre, des accents et de la ponctuation. Sinon un nouveau chemin est proposé,
avec les genres dans leur ordre fourni par vidb, séparés par une virgule et une espace.
La proposition ne crée aucun dossier : la sélection de destination le crée après
validation. Les noms contenant des séparateurs de chemin sont refusés. En cas de
plusieurs dossiers équivalents, conserver le choix manuel plutôt que d'en privilégier un.

Exemple : 1917, pays Royaume-Uni, genres Guerre et Histoire :
`/videos/Films/Guerre, Histoire/1917 (1917).mkv`.
La convention des titres selon les pays reste appliquée par title_convention.
Les projets enregistrés et tâches déjà en file ne sont ni déplacés ni réécrits.

## Collections et séries documentaires

Si vidb transmet `destination_container`, sa collection ou série parente ajoute
un dossier après les genres pour les films, après Documentaires pour les documentaires.
Les titres du parent suivent la même convention de pays que les œuvres.
Un dossier existant unique correspondant au titre du parent est réutilisé,
y compris avec une année en suffixe. Sinon le chemin du parent est proposé sans
création avant validation. L’appartenance n’est jamais devinée par recherche externe.
Les épisodes avec une saison gardent leur placement Série/Saison NN/Épisode.mkv.
