# Revoir une proposition avant enregistrement

La passerelle conserve le nouveau lien `selection_url`, uniquement s'il reste
sur l'origine HTTPS vidb configurée. Le menu d'identification privilégie ce lien
pour les projets déjà identifiés ; le lien de complément ancien reste un repli.

Le choix du nom et du dossier propose « Revoir la proposition vidb… ». La fiche
peut être corrigée ou remplacée après confirmation dans vidb. Au retour, la
destination est recalculée depuis les métadonnées actualisées. L'extension reste
celle demandée (.json pour le projet, .mkv pour la vidéo). La révision n'enregistre
aucun projet et ne met aucun encodage en file par elle-même.

Le même accès existe dans l'avertissement de durée. Après cette révision,
l'enregistrement courant est interrompu : sa destination peut ne plus convenir.
Le montage et ses segments restent ouverts. Il faut relancer la préparation
pour revoir la destination et le contrôle de durée avant toute écriture.

Les identifiants du projet sont conservés. Les références de durée mises en
mémoire sont invalidées après confirmation. Revenir au montage ne supprime pas
silencieusement une association ; elle reste réexaminable par le menu ou la barre.
Les fichiers existants et les tâches de la file ne sont pas modifiés lors du retour.
