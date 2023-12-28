# beets-autogenre

A [beets](https://github.com/beetbox/beets) plugin to assign genres to all items within your music library.

## Features

* Gets genres from last.fm using the [lastgenre plugin](https://beets.readthedocs.io/en/stable/plugins/lastgenre.html).
* Fallback to estimating the genre using the [xtractor plugin](https://github.com/adamjakab/BeetsPluginXtractor) / [Essentia](https://essentia.upf.edu/).
* Fixes the genre of (re)mixes by matching the genre tree against the track and album title.
* Allows to specify the genre per item manually.

## Dependencies

The following beets plugins and their dependencies must be installed:
* [lastgenre plugin](https://beets.readthedocs.io/en/stable/plugins/lastgenre.html).
* [xtractor plugin](https://github.com/adamjakab/BeetsPluginXtractor) which relies on [Essentia](https://essentia.upf.edu/).

## Installation

```sh
python3 -m pip install beets-autogenre
```

## Configuration

Enable the plugin and add a `autogenre` section to your beets `config.yaml` as follows:
```yaml
plugins:
  - autogenre
  - lastgenre
  - xtractor

autogenre:
  pretend: false
  all: false
  force: false
  lastgenre: true
  xtractor: true
  remix_title: true
  genre_rosamerica_strong: 0.8
  genre_electronic_strong: 0.8
  genre_electronic_prepend: 0.5
  genre_electronic_append: 0.45

lastgenre:
  auto: false
  prefer_specific: true
  source: track
  count: 4
  min_weight: 15
  canonical: /etc/beets/genre-tree.yaml
  whitelist: /etc/beets/genres.txt

xtractor:
  auto: no
  dry-run: no
  write: yes
  threads: 4
  force: no
  quiet: no
  keep_output: no
  keep_profiles: no
  output_path: /tmp/xtractor
  essentia_extractor: /usr/local/bin/essentia_streaming_extractor_music
  high_level_targets:
    genre_rosamerica_probability: # 0..1
      path: "highlevel.genre_rosamerica.probability"
      type: float
    genre_electronic:
      path: "highlevel.genre_electronic.value"
      type: string
    genre_electronic_probability: # 0..1
      path: "highlevel.genre_electronic.probability"
      type: float
    timbre: # "dark" or "bright"
      path: "highlevel.timbre.value"
      type: string
    tonal_atonal: # "tonal" or "atonal"
      path: "highlevel.tonal_atonal.value"
      type: string
    key_edma: # e.g. "C#"
      path: "tonal.key_edma.key"
      type: string
    key_edma_scale: # e.g. "minor"
      path: "tonal.key_edma.scale"
      type: string
  extractor_profile:
    highlevel:
      svm_models:
        - /var/lib/essentia/svm-models/beta5/danceability.history
        - /var/lib/essentia/svm-models/beta5/gender.history
        - /var/lib/essentia/svm-models/beta5/genre_rosamerica.history
        - /var/lib/essentia/svm-models/beta5/genre_electronic.history
        - /var/lib/essentia/svm-models/beta5/mood_acoustic.history
        - /var/lib/essentia/svm-models/beta5/mood_aggressive.history
        - /var/lib/essentia/svm-models/beta5/mood_electronic.history
        - /var/lib/essentia/svm-models/beta5/mood_happy.history
        - /var/lib/essentia/svm-models/beta5/mood_sad.history
        - /var/lib/essentia/svm-models/beta5/mood_party.history
        - /var/lib/essentia/svm-models/beta5/mood_relaxed.history
        - /var/lib/essentia/svm-models/beta5/moods_mirex.history
        - /var/lib/essentia/svm-models/beta5/voice_instrumental.history
        - /var/lib/essentia/svm-models/beta5/tonal_atonal.history
        - /var/lib/essentia/svm-models/beta5/timbre.history
```

For more information, see [CLI](#cli).

## Usage

Once the `autogenre` plugin is enabled within your beets configuration, you can detect and assign the genres for each track within your library as follows:
```sh
beet autogenre
```

### CLI

```
Usage: beet autogenre [options]

Options:
  -h, --help          show this help message and exit
  --pretend           do not persist item changes but log them
  -f, --force         reevaluate genres for items with a matching genre_source
  -a, --all           overwrite genre if genre_source not specified
  --no-all            do not overwrite genre from unspecified source
  --lastgenre         use lastgenre plugin
  --no-lastgenre      do not use lastgenre plugin
  --xtractor          use xtractor plugin
  --no-xtractor       do not use xtractor plugin
  --remix-title       derive genre from remix title
  --no-remix-title    do not derive genre from remix title
  --parent-genres     add primary genre's parent genres
  --no-parent-genres  do not add primary genre's parent genres
  --genre=GENRE       specify the genre to assign to the selected items
```

## Development

Run the unit tests (containerized):
```sh
make test
```

Run the e2e tests (containerized):
```sh
make test-e2e
```

To test your plugin changes manually, you can run a shell within a beets docker container as follows:
```sh
make beets-sh
```

A temporary beets library is written to `./data`.
It can be removed by calling `make clean-data`.
