# Commandes générales du menu Montage de vidb

Le protocole existant accepte une seconde entrée :
`vidb-encoder://desktop?ticket=...&origin=...`.
L’entrée `prepare` reste réservée à la préparation depuis une fiche.

La demande `desktop` est authentifiée par la passerelle habituelle. Son jeton
utilise un usage de signature distinct et ne contient qu’une action choisie
parmi quatre commandes : `new_montage`, `open_project`, `encode_dvd`, `show_queue`.
Le client vérifie cette liste avant d’appeler les contrôleurs existants. Le
serveur refuse de combiner une commande générale avec une association de projet.

Aucun chemin, nom de commande système ou fonction arbitraire n’est accepté dans
le lien. L’utilisateur choisit le fichier ou le disque dans l’interface native.
Les dialogues et contrôles d’enregistrement existants restent responsables de
la protection du montage ouvert. Une erreur est signalée sans repli vers une
autre action.

La même instance locale reçoit les demandes, avec le verrou et la sérialisation
des dialogues du premier lot. Aucune nouvelle file d’encodage, aucun démon et
aucune réinstallation du lanceur ne sont nécessaires. Relancer seulement
l’interface après la fin des encodages pour charger le nouveau répartiteur.

Le lancement direct de `bin/video_encoder_ui` ou de son raccourci de bureau est
inchangé. Les commandes de vidb sont des entrées supplémentaires vers ces mêmes
fonctions ; elles ne remplacent pas l’utilisation autonome de video_encoder.
