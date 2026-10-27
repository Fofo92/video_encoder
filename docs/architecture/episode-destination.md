# Destination des épisodes

La fiche vidb fournit les titres de série, le numéro de saison et le rang de l’épisode.
Le nom proposé est `Sxx Exx - Titre français (Titre original).mkv`, sans préfixe
de série ni suffixe « valide ». Le titre original connu est conservé, y compris
lorsqu’il est identique pour une œuvre étrangère.
Les dossiers existants sous /videos/Séries TV, _complet et _incomplet sont examinés.
Les anciens compteurs entre parenthèses ne sont pas modifiés. Les apostrophes et accents
n’empêchent pas de reconnaître la série. Un dossier de série unique et son dossier
de saison existant sont privilégiés ; si cette saison manque, `Saison NN` est proposé.
Sans série unique, une proposition initiale sous `/videos` utilise `/videos/Séries TV`.
Un autre dossier déjà choisi est conservé. L’utilisateur peut saisir le chemin complet :
les sous-dossiers manquants sont créés lors de la validation. Aucun fichier existant
n’est déplacé ni écrasé.

Voir [Destination des épisodes et sous-dossiers](nested-episode-destination.md).
