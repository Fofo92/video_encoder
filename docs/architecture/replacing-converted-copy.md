# Reprendre le nom de la copie source après conversion

Le renommage d’un projet copy_version terminé vers le nom de sa source constitue
un remplacement explicite. L’aperçu existant affiche les fichiers qui seront
archivés et ceux qui reprendront le nom initial. La confirmation reste nécessaire.

Le JSON d’origine doit être présent ; si l’utilisateur l’a placé dans la corbeille
Plasma, il doit d’abord le restaurer. Restaurer aussi l’ancien MKV s’il est encore
récupérable. Si ce MKV est déjà absent, le reçu conserve cette absence et la source
historique ne sera jamais assimilée au nouveau MKV.

Le traitement, sérialisé avec les workers par SQLite BEGIN IMMEDIATE :

1. Vérifie le reçu de réussite VOST, les identités et les tâches concernées.
2. Archive l’ancien projet, sa vidéo si présente et son reçu dans la corbeille
   video_encoder, avec un manifeste de récupération.
3. Réécrit la référence source du projet VOST vers l’archive et actualise son reçu.
4. Publie la VOST au nom initial et met à jour les chemins des deux tâches.

Les états des tâches ne changent pas. Un travail en cours, en attente ou reporté,
une source différente, un reçu périmé ou une autre préparation dépendante bloque
l’opération. Une erreur avant validation SQLite restaure les fichiers et la file.
L’aperçu n’écrit aucun fichier ni aucune référence.

L’archive est inscrite dans la corbeille existante, avec sa rétention habituelle.
Après expiration de l’ancienne source, reprendre une version depuis le MKV final
reste possible ; rejouer l’ancien traitement depuis sa source disparue ne l’est
plus. L’application ne remplace jamais cette source par la sortie elle-même.

vidb doit aussi recevoir le correctif d’import du remplacement : l’ancienne
référence VM est archivée, et la copie VOST déjà connue est déplacée vers le nom
final, sans créer de doublon ni changer l’état de visionnage.
