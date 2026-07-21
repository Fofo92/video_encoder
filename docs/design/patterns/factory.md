## Factory

### Contexte

L'encodage doit créer un moniteur adapté au fichier source afin de suivre la
progression de FFmpeg.

`FFmpegEncoder` utilise ce moniteur pendant l'exécution, mais il n'a pas besoin
de connaître les détails nécessaires à sa construction.

### Mise en œuvre

La création du moniteur est confiée à `EncodingMonitorFactory`.

L'encodeur demande simplement à la Factory de construire un moniteur pour la
source courante :

```ruby
monitor = @monitor_factory.build(source)
```

Il utilise ensuite l'objet retourné à travers son interface publique :

```ruby
monitor.call(stream, line)
monitor.finish
```

### Motivation

Cette séparation évite à `FFmpegEncoder` de cumuler deux responsabilités :

* piloter l'encodage ;
* connaître la manière de construire son moniteur de progression.

Elle permet également d'injecter une Factory de remplacement dans les tests et
de faire évoluer la création des moniteurs sans modifier l'encodeur.

Cette mise en œuvre correspond au pattern **Factory**.
