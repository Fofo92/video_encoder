# Contrôle de durée avant enregistrement du montage

Lorsque l’identification vidb renvoie `metadata.reference_runtime_minutes`, la
fenêtre de montage compare cette durée indicative à la somme de tous les segments
conservés. Les bornes IN/OUT sont inclusives. La cadence rationnelle exacte du
profil est utilisée ; les montages multisource existants imposent déjà une
cadence commune. Aucune inspection supplémentaire des captures n’est lancée.

Le contrôle intervient au début de `write_project`, donc avant l’écriture du
JSON, le nettoyage des intermédiaires et le lancement du contrôle audio, pour
l’enregistrement manuel, la mise en file et l’export immédiat.

Une différence **strictement supérieure au maximum de trois minutes et de 10 %
de la durée attendue** ouvre un avertissement : « Revenir au montage » (choix par
défaut) ou « Continuer malgré l’écart ». Exemple : pour 40 minutes attendues,
36 et 44 minutes sont tolérées ; 27 minutes déclenchent un avertissement.

Fermer l’avertissement ou revenir au montage n’écrit pas le projet et ne lance
aucun encodage. Continuer autorise cet enregistrement, sans mémoriser une exemption
pour les enregistrements futurs. La durée attendue, les segments et la cadence
sont relus à chaque tentative. Un projet déjà existant reste intact en cas de
retour au montage.

Si la durée attendue ou les données de calcul sont absentes ou invalides, le
contrôle est omis. Il ne bloque pas un travail hors connexion ou sans fiche.
Aucune comparaison avec la longueur totale des sources n’est faite. Ce contrôle
ne vérifie ni les doublons de contenu ni l’exhaustivité du programme.

Déployer d’abord vidb pour transmettre la durée catalogue puis redémarrer
video_encoder après installation du correctif, sans interrompre les encodages.
Les anciennes réponses sans ce champ restent compatibles.
