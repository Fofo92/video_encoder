# Point d’entrée local depuis vidb

Le protocole `vidb-encoder://prepare?ticket=...&origin=...` transporte une demande
signée et non un chemin de fichier ou une commande système. L’origine doit
correspondre à la passerelle HTTPS configurée. La résolution et l’association
utilisent son authentification actuelle ; l’utilisateur choisit la source dans
une boîte de dialogue locale.

`DesktopInbox` fournit une entrée locale réservée au compte Unix courant.
Une interface déjà ouverte reçoit la demande ; une nouvelle interface n’est
pas lancée en concurrence. Les dialogues de plusieurs demandes sont traités
successivement. Un doublon visant le montage déjà ouvert ramène sa fenêtre au
premier plan. Une livraison non confirmée ne déclenche jamais une seconde
instance par repli.

Les anciennes interfaces sans entrée locale sont détectées en lecture seule
dans `/proc`. Aucun processus n’est arrêté. Les processus Ruby d’encodage et les
tests Python ne sont pas pris pour une interface. Le mécanisme n’ouvre aucun port
TCP et n’ajoute aucun démon.

Un `QLockFile` réservé au compte courant protège l’entrée avant toute écoute.
Il est conservé pendant la vie de l’interface, sans expiration fondée sur son
âge, puis libéré à la fermeture ou si le démarrage échoue. Une connexion préalable
vérifie aussi que le nom d’écoute n’appartient pas déjà à une autre interface.

Le choix explicite de fiche est conservé dans `session.vidb_launch`, puis dans
le projet si nécessaire. `VidbProjectLink` l’utilise avant toute recherche par
titre. La fiche n’est effectivement associée que lors de l’identification ou
de l’enregistrement du montage, via les services existants de vidb. Après
identification, le jeton temporaire est retiré au prochain enregistrement ; la
liaison signée normale subsiste. Un changement de fiche confirmé ultérieurement
dans vidb garde priorité sur la demande de lancement initiale.

L’ouverture seule ne lance aucun export, aucune mise en file, aucun déplacement
et aucun contrôle automatique de quarantaine au démarrage par protocole. Les
commandes habituelles de l’éditeur et la file actuelle restent responsables des
étapes suivantes.

Installation du protocole pour le compte graphique, sans sudo :

```bash
cd ~/code/Fofo92/video_encoder &&
python3 bin/install-vidb-launcher
```

Le mode `--dry-run` ne modifie rien. Le lanceur appelle le script `bin/video_encoder_ui`
du dépôt et reste donc valable après les mises à jour à cet emplacement. Si le
dépôt est déplacé, réexécuter l’installateur pour actualiser son chemin.

Fermer l’ancienne interface après la fin des encodages puis relancer video_encoder
pour activer la réception des demandes. Depuis un autre poste, le protocole viserait
l’éditeur de cet autre poste ; l’accès distant à la base reste indépendant.
