# Mettre plusieurs sources en quarantaine

Depuis Sources → Mettre des sources en quarantaine, le sélecteur accepte plusieurs fichiers (Ctrl/clic ou Maj/clic). Une seule confirmation porte sur toute la sélection : tous les programmes utiles de chaque source doivent avoir été encodés. L’option par défaut reste Non.

Les fichiers sont déplacés par la commande de quarantaine habituelle, jamais supprimés définitivement. Les protections du backend restent appliquées séparément à chaque source, notamment lorsqu’une tâche en attente ou en cours l’utilise.

Le contrôleur déduplique la sélection et poursuit les autres fichiers après un refus ou une erreur système. Le bilan final indique les sources déplacées et celles conservées avec leur motif. Il n’y a pas de confirmation ni de notification de succès répétée pour chaque fichier.

L’appel unitaire du contrôleur reste compatible. Cette action manuelle est indépendante du protocole de confirmation de fin d’utilisation des sources après encodage. Le lot ne déclenche aucune purge de quarantaine.
