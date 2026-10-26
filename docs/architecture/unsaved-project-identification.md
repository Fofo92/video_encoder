# Identifier un montage avant sa sauvegarde

L’action « Identifier l’œuvre dans vidb » consulte la passerelle avec les sources et l’identifiant du montage ouvert. Elle n’appelle plus la sauvegarde du projet ni le choix de destination : une annulation dans ce parcours ne peut donc plus interrompre silencieusement l’identification.

Le lien de proposition fourni par vidb s’ouvre directement dans la fenêtre intégrée. Après fermeture, la passerelle est consultée de nouveau pour conserver l’association dans la session. Celle-ci sera écrite dans le projet lors de sa sauvegarde habituelle. Aucune tâche d’encodage n’est ajoutée par l’action d’identification.

L’absence de configuration, l’indisponibilité de vidb ou une réponse sans lien sont signalées explicitement. Une erreur de construction de la fenêtre web reste affichée dans le dialogue ; un échec de chargement de page ou l’arrêt du moteur web affiche également un message. Les détails internes et les jetons des liens ne sont pas exposés.

Les tests couvrent le montage non sauvegardé, la réutilisation de son identifiant, la conservation des segments, le cas déjà identifié et les indisponibilités. L’affichage natif de Qt WebEngine reste à vérifier sur le poste utilisateur.

Les actions Sources/Projets de l’accueil appartiennent explicitement à la fenêtre d’accueil, et les menus sont conservés par cette fenêtre. Une reconstruction de menu ne doit pas détruire les QAction encore utilisées par le contrôleur d’édition.

Pour diagnostiquer un problème natif non reproduit par les tests : `VIDEO_ENCODER_VIDB_DEBUG=1 bin/video_encoder_ui`. Les messages `[vidb-window]` décrivent l’état de la passerelle, le chargement de page et les événements de la fenêtre. Ils ne contiennent ni URL, ni jeton, ni texte saisi. Ce mode est désactivé par défaut.
