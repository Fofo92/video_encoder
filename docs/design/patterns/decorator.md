# Decorator

## Contexte

L’export d’un `TrimProject` produit plusieurs fichiers intermédiaires dans un workspace dédié :

- le projet MLT ;
- les flux vidéo et audio temporaires ;
- les segments de sous-titres ;
- les manifestes de concaténation ;
- les fichiers SRT générés par OCR.

Après un export réussi, ces fichiers n’ont plus d’utilité et le workspace peut être supprimé.

En revanche, lorsqu’un export échoue, ils doivent être conservés afin de faciliter le diagnostic.

Cette politique de nettoyage appartient au cycle de vie de l’export, mais pas à la responsabilité
 principale de `TrimExporter`, qui consiste à produire le média final.

## Mise en œuvre retenue

Le nettoyage est confié à `WorkspaceCleaningExporter`.

Ce composant enveloppe le service d’export et présente la même interface publique.
Son fonctionnement est le suivant :

1. déléguer l’export au service encapsulé ;
2. attendre que cet export se termine avec succès ;
3. supprimer le workspace ;
4. retourner le résultat du service encapsulé.

```ruby
class WorkspaceCleaningExporter
  def initialize(exporter:, workspace:)
    @exporter = exporter
    @workspace = workspace
  end

  def call(...)
    result = exporter.call(...)

    workspace.cleanup
    result
  end

  private

  attr_reader :exporter, :workspace
end
```

Si le service encapsulé lève une exception, l’instruction de nettoyage n’est  pas exécutée.
Le workspace reste donc disponible pour établir le diagnostic.

Le nettoyage ne doit volontairement pas être placé dans une clause `ensure` :

```ruby
def call(...)
  exporter.call(...)
ensure
  workspace.cleanup
end
```

Cette forme supprimerait également les fichiers intermédiaires après un échec.

## Composition

La composition est réalisée par `TrimExportFactory` :

```ruby
exporter = TrimExporter.new(
  builder: builder,
  renderer: renderer,
  remuxer: remuxer,
  workspace: workspace,
  subtitle_exporter: subtitle_exporter
)

cleaning_exporter = WorkspaceCleaningExporter.new(
  exporter: exporter,
  workspace: workspace
)
```

Le service applicatif reçoit le décorateur sans avoir besoin de connaître son
 fonctionnement interne :

```text
ExportTrimProject
        │
        ▼
WorkspaceCleaningExporter
        │
        ▼
TrimExporter
```

`WorkspaceCleaningExporter` et `TrimExporter` respectent le même contrat d’appel.
 Le premier peut donc remplacer le second auprès de son client.

## Responsabilités

### `TrimExporter`

- construit le projet MLT ;
- lance le rendu vidéo et audio ;
- produit éventuellement les sous-titres ;
- remultiplexe les flux ;
- retourne le résultat de l’export.

### `WorkspaceCleaningExporter`

- délègue l’export ;
- nettoie le workspace uniquement après un succès ;
- préserve le résultat retourné ;
- laisse remonter les erreurs sans supprimer les fichiers de diagnostic.

### `TrimWorkspace`

- connaît les chemins des fichiers intermédiaires ;
- écrit les fichiers nécessaires ;
- supprime son répertoire de travail lorsqu’un nettoyage lui est demandé.

## Motivation

Cette organisation évite d’ajouter une nouvelle responsabilité à  `TrimExporter`.

Elle permet également :

- de tester indépendamment la politique de nettoyage ;
- de conserver les fichiers intermédiaires après un échec ;
- d’appliquer la même politique depuis la CLI ou une future application Rails ;
- de remplacer ou retirer le nettoyage sans modifier le pipeline d’export ;
- de maintenir une séparation claire entre l’export et le cycle de vie de ses
   ressources temporaires.

Cette mise en œuvre correspond au pattern **Decorator**.

## Pourquoi pas un Adapter ?

Un Adapter transforme une interface afin de la rendre compatible avec un  client.

Ici, l’interface du service d’export ne change pas.
 `WorkspaceCleaningExporter` ajoute un comportement autour de l’appel existant.

## Pourquoi pas directement dans `TrimExporter` ?

`TrimExporter` orchestre déjà la production du média final. Lui confier aussi la politique de conservation
 ou de suppression des fichiers intermédiaires mélangerait deux raisons de changer :

- l’évolution du pipeline audiovisuel ;
- l’évolution de la politique de nettoyage.

Le décorateur maintient ces responsabilités séparées.

## Limites

L’ordre des décorateurs devient significatif si d’autres comportements sont
 ajoutés ultérieurement, par exemple la journalisation ou la mesure de durée.

La composition devra donc rester explicite dans la Factory afin que le cycle d’exécution soit facile à comprendre.

```

Puis complète le fichier d’index.

### Fichier : `docs/design/patterns/index.md`

Après le paragraphe introductif existant, ajoute :

```markdown
## Patterns documentés

- [Decorator](decorator.md) — nettoyage du workspace après un export réussi ;
- [Factory](factory.md) — construction des collaborateurs techniques ;
- [Repository](repository.md) — persistance des travaux d’encodage.
```

```ruby
exporter.call(
  trim_project: trim_project,
  output_path: output_path
)
