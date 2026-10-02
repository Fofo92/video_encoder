# Factory

## Contexte

L’export d’un montage nécessite plusieurs adaptateurs techniques : chargement
du projet, analyse des médias, rendu MLT, traitement des sous-titres,
remultiplexage FFmpeg et nettoyage du workspace.

Les commandes et l’interface graphique ne doivent pas connaître les détails de
leur assemblage.

## Mise en œuvre

`TrimProjectFileExportFactory` construit le service qui charge un projet
persistant. Elle délègue à `TrimExportFactory` la composition du service
d’export.

`TrimExportFactory` assemble notamment :

- `ExportTrimProject` et `TrackSelector` ;
- `TrimExporter` ;
- `MltProjectBuilder` et `MltRenderer` ;
- la chaîne de traitement des sous-titres DVB ;
- `FfmpegRemuxer` ;
- `WorkspaceCleaningExporter`.

L’appelant fournit uniquement les dépendances d’infrastructure et le chemin du
workspace, puis utilise le service retourné à travers son interface publique.

## Motivation

Cette séparation centralise la construction d’une chaîne d’export cohérente,
évite de dupliquer son câblage entre la CLI et l’interface graphique et permet
d’injecter des collaborateurs de remplacement dans les tests.

Cette mise en œuvre correspond au pattern **Factory**.
