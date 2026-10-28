# Sélection des pistes selon la langue originale

Avant le contrôle audio, la mise en file et l’export immédiat, le montage utilise
la langue originale de l’œuvre identifiée dans vidb. La seule présence d’une
piste `qaa` ne prouve pas que la VO est étrangère.

vidb consulte TMDB avec les identifiants de connexion déjà configurés pour ses
recherches. Il exige un film unique dont le titre et l’année concordent, puis
vérifie à nouveau le détail du film. Les épisodes ne sont pas recherchés comme
des films. Les œuvres multilingues, les homonymes ambigus, les années absentes,
les erreurs réseau ou une configuration TMDB absente conduisent à une validation
manuelle, jamais à une déduction depuis le pays ou le titre. Les requêtes sont
bornées et le résultat est mis en cache dix minutes.

- VO française : une sortie audio française ; pas de traitement des sous-titres
  complets, ordinaires ou pour malentendants. Les sous-titres explicitement
  marqués forcés et français restent conservés. Si une source n’a pas de piste
  française, le contrôle échoue explicitement plutôt que de substituer `qaa`.
- VO étrangère : parcours existant français + VO et sous-titres français.
- Langue incertaine : choix « Oui, VO française », « Non, VO étrangère » ou
  « Revenir au montage », qui est le choix par défaut. Aucun contrôle audio,
  OCR ou encodage ne démarre si la boîte est fermée ou annulée.

Le choix et la provenance de la décision sont stockés dans `track_selection`
dans le JSON du projet, avec son identité, la fiche et les chemins des sources.
Il est conservé à la réouverture et à la sauvegarde, et redemandé si la fiche ou
les sources changent. Le moteur Ruby respecte ce choix au contrôle audio et à
l’export. Les projets sans ce champ gardent le comportement existant : rouvrir
et remettre en file un ancien projet pour bénéficier du nouveau filtrage.

Le contrôle de durée v2 et la présentation compacte du contrôle audio sont
conservés. Le correctif ne modifie pas un encodage déjà lancé.
