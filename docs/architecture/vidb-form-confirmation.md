# Attendre la validation du formulaire vidb

Le dialogue avant mise en file ne se ferme plus parce qu’un rafraîchissement a simplement reconnu une fiche ou modifié ses métadonnées. Le formulaire vidb signale sa validation réussie par une redirection vers `/records/ID?encoder_prepared=1`.

Le navigateur n’accepte ce signal que sur la même origine HTTPS que la page vidb attendue. Le parcours d’export attend ensuite que la passerelle fournisse une association au même numéro de fiche avant de reprendre la destination, les contrôles audio et la mise en file habituels. Le marqueur d’URL n’autorise aucune opération serveur ; l’association reste contrôlée par vidb.

La consultation manuelle se ferme après la validation du formulaire et rafraîchit l’association du montage. Les décisions différées de l’atelier de réconciliation conservent leur parcours existant. En l’absence du nouveau volet serveur, le dialogue reste ouvert et le bouton de continuation explicite reste disponible.

Les tests vérifient qu’une reconnaissance automatique seule ne ferme rien, qu’une confirmation d’une autre fiche ne reprend pas l’encodage, et que la validation de données inchangées fonctionne. Aucun traitement du média, de la souris ou du ShuttleXpress n’est modifié.
