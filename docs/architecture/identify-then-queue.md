# Identifier puis mettre le montage en file

Quand les plages sont prêtes, **Montage → Identifier et mettre en file…**
(`Ctrl+Maj+E`, également disponible par l’icône de mise en file) conduit le
parcours complet : identification, destination, enregistrement, contrôle audio,
puis ajout de la tâche. L’encodage immédiat réutilise le même parcours d’identification.

Si une association reste à valider, vidb s’ouvre directement dans une fenêtre
modale de video_encoder, sans onglet du navigateur externe.
video_encoder garde le parcours en attente et interroge la passerelle en arrière-plan,
sans bloquer le thread de l’interface. Une seule consultation est active à la fois.
Une association confirmée reprend le choix de destination sans relancer de menu.
Les genres et titres obtenus dans vidb servent au classement et au nom proposés.

Le dialogue permet aussi de **Continuer sans association** lorsque l’identification
ne peut pas aboutir, ou de **Revenir au montage** en conservant toutes les plages.
Une indisponibilité réseau ne vaut jamais validation ni autorisation de continuer.
Sans association, le projet reste à consolider comme dans le parcours antérieur.
Le choix de dossier et le contrôle audio final restent disponibles avant toute mise en file.

La commande **Compléter la fiche dans vidb** du récapitulatif d’épisode garde
également le parcours en attente. Une modification des métadonnées reprend le
choix de destination. Si les valeurs restent identiques, **Continuer avec la fiche
actuelle** permet de reprendre explicitement. Une panne réseau conserve une
association déjà confirmée.

La page web ne notifie pas directement video_encoder : la passerelle existante
est consultée environ toutes les trois secondes après réception d’une réponse.
Le document et son identifiant de projet restent en mémoire jusqu’à l’enregistrement
habituel du JSON. Aucun nouveau fichier d’échange ni service permanent n’est ajouté.
Les requêtes utilisent le délai réseau borné déjà défini dans VidbProjectLink.

Les commandes dédiées à la sauvegarde ou à la consultation manuelle de vidb restent
indépendantes ; elles ne mettent pas de montage en file automatiquement.


## Fenêtre vidb intégrée

Sur Debian 13, installer `python3-pyside6.qtwebenginewidgets` avec apt puis
relancer video_encoder. Le lanceur utilise `/usr/bin/python3`. Si le composant
manque, le dialogue indique son installation et n’ouvre pas d’onglet externe.
La première ouverture peut demander une connexion habituelle à vidb. La session
web est distincte de celle du navigateur et du secret de la passerelle ; aucun
secret Bearer n’est injecté dans la page ou son URL.

Les cookies de session sont conservés dans un profil privé par serveur sous
`$XDG_DATA_HOME/video_encoder/vidb-browser` (par défaut
`~/.local/share/video_encoder/vidb-browser`). Le cache HTTP reste en mémoire.
Les liens demandant une nouvelle fenêtre réutilisent la page intégrée.
Les consultations manuelles de la fiche depuis video_encoder utilisent aussi
une fenêtre modale, sans lancer de mise en file par elles-mêmes.

## Enchaîner après le montage en cours

Pendant l’exécution isolée d’un montage, ou après avoir demandé l’arrêt de la
file à la fin du montage courant, le bouton de lancement devient **Enchaîner
après le montage en cours**. Un clic programme la suite et affiche **Suite
programmée**. Aucun second worker n’est lancé avant la fin du worker actuel.
À sa fin, la file normale reprend les tâches en attente dans leur ordre habituel.

Une interruption volontaire annule cette programmation. Une nouvelle demande
d’arrêt après le montage en cours l’annule également. Si le montage isolé échoue,
la suite n’est lancée que si elle avait été explicitement demandée ; l’échec reste
signalé. La demande d’enchaînement reste locale à l’application ouverte.
