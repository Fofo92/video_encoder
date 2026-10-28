# Présentation du contrôle audio

La confirmation avant mise en file ou export affiche des rubriques en gras et
une destination compacte : le dossier et le nom commun ne sont présentés qu’une
fois, avec les extensions du projet et de la vidéo. Les pistes sont regroupées
par fichier source. Si deux sources ont le même nom dans des dossiers différents,
leurs chemins sont affichés pour les distinguer.

Les détails dépliables conservent les chemins complets du projet, de la vidéo et
de chaque source, en texte brut copiable. Les valeurs provenant des chemins ou
du rapport sont échappées avant insertion dans le texte riche Qt.

La grande icône de question est retirée. Les boutons Ajouter à la file / Exporter
et Annuler ne changent pas de comportement : Annuler reste le choix par défaut.
Le contrôle mesure le signal, pas la langue ; un résultat non concluant demeure
explicitement signalé. Aucun traitement audio ou vidéo n’est ajouté.
