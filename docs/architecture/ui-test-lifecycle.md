# Cycle de vie Qt dans les tests de l’IHM

`bin/check` utilise `python3 -X faulthandler ui/run_tests.py`. Le lanceur garde
une QApplication pendant toute la suite et choisit la plateforme `offscreen`
par défaut, sans changer la plateforme de l’application vidéo normale.
Il conserve la découverte `test_*.py` et le statut d’échec de unittest.

À la fin, les arbres de widgets sont détruits avec les événements
`DeferredDelete` avant le nettoyage Python et la fermeture de QApplication.
Un simple `processEvents()` ne garantit pas ce traitement hors boucle `exec()`.
Le lanceur ne masque aucun crash, n’utilise pas `os._exit` et ne saute aucun test.

Les tests du navigateur vidb simulent `QDialog.exec`. Leur fixture conserve les
dialogues créés, fixe leur taille sans accéder à un écran natif, puis détruit
explicitement les dialogues et leurs enfants après les nettoyages individuels.
Le calcul de taille de production reste inchangé et dispose de trois tests
séparés : petit écran, plafond sur grand écran et écran absent.

Ce correctif vise le cycle de vie des objets dans les tests ; il ne permet pas
d’attribuer le blocage de Plasma ou la latence Firefox à cette même cause.
