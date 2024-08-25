import codecs
import mediafile
import os
import re
import yaml
from collections import Counter
from beets.plugins import BeetsPlugin
from beets.dbcore import types
from beets.dbcore.query import FixedFieldSort
from beets.library import Item, parse_query_parts
from beets.ui import Subcommand, decargs
from beets import config
from optparse import OptionParser
from confuse import ConfigSource, load_yaml
from beetsplug.lastgenre import LastGenrePlugin
from beetsplug.xtractor import XtractorCommand
from beetsplug.autogenre.genretree import GenreTree

# See https://essentia.upf.edu/svm_models/accuracies_v2.1_beta1.html
ROSAMERICA_GENRES = {
    'cla': 'classical',
    'dan': 'dance', # CAUTION: 'dance' is an out-of-tree genre: might be electronic or rock. better set genre of those tracks manually.
    'hip': 'hip hop',
    'jaz': 'jazz',
    'pop': 'pop',
    'rhy': 'rhythm and blues',
    'roc': 'rock',
    'spe': 'speech'
}
ELECTRONIC_GENRES = {
    'ambient': 'ambient',
    'dnb': 'drum and bass',
    'house': 'house',
    'techno': 'techno',
    'trance': 'trance',
}
SOURCES = set(('lastfm', 'title', 'essentia', 'user'))

class AutoGenrePlugin(BeetsPlugin):
    item_types = {
        'genre_source': types.STRING,
        'genres': types.STRING,
    }

    @property
    def album_types(self):
        return self.item_types

    def __init__(self):
        super(AutoGenrePlugin, self).__init__()
        config_file_path = os.path.join(os.path.dirname(__file__), 'config_default.yaml')
        source = ConfigSource(load_yaml(config_file_path) or {}, config_file_path)
        self.config.add(source)
        assert _is_plugin_enabled('lastgenre'), "The 'lastgenre' plugin is not enabled!"
        assert _is_plugin_enabled('xtractor'), "The 'xtractor' plugin is not enabled!"
        self._lastgenre = LastGenrePlugin()
        self._xtractor = XtractorCommand(config['xtractor'])
        self._lastgenre_conf = config['lastgenre'].get() or {}
        self._separator = self._lastgenre_conf.get('separator') or ', '
        self._remix_regex = re.compile(r'.+[^\w](remix|bootleg|remake)', re.IGNORECASE)
        self._genre_tree = None
        # TODO: fix auto support - fix genres field mapping, see https://github.com/beetbox/mediafile/blob/master/mediafile.py#L1814
        if self.config['auto'].get(bool):
            self.import_stages = [self.imported]

    def imported(self, session, task):
        """Event hook called when an import task finishes."""
        if task.is_album:
            for item in task.album.items():
                self._update_item_genre(item)

            self._update_album_genre(task.album)
        else:
            self._update_item_genre(task.item)

    def _update_item_genre(self, item):
        genre, genres, source = self._item_genre(item, True, True)
        self._log.info("Set track genre '{}' ({}): {}", genre, source, item)
        item.genre = genre
        item.genres = genres
        item.genre_source = source
        if not self.config['pretend'].get():
            if config['import']['write'].get():
                item.try_write()
            item.store(['genre'])
            item.store(['genres', 'genre_source'])

    def _update_album_genre(self, album):
        genre = _most_common([item.genre for item in album.items()])
        if album.genre != genre and genre:
            album.genre = genre
            self._log.info("Set genre '{}' for album {}", album.genre, album)
            if not self.config['pretend'].get():
                album.store(['genre'])

    def commands(self):
        p = OptionParser()
        p.add_option('--pretend', action='store_true',
            default=self.config['pretend'].get(),
            help='do not persist item changes but log them')
        p.add_option('-f', '--force', action='store_true',
            default=self.config['force'].get(),
            help='reevaluate genres for items with a matching genre_source')
        p.add_option('-a', '--all', action='store_true',
            default=self.config['all'].get(),
            dest='all', help='overwrite genre if genre_source not specified')
        p.add_option('--no-all', action='store_false',
            default=self.config['all'].get(),
            dest='all', help='do not overwrite genre from unspecified source')
        p.add_option('--lastgenre', action='store_true',
            default=self.config['lastgenre'].get(),
            dest='lastgenre', help='use lastgenre plugin')
        p.add_option('--no-lastgenre', action='store_false',
            default=self.config['lastgenre'].get(),
            dest='lastgenre', help='do not use lastgenre plugin')
        p.add_option('--xtractor', action='store_true',
            default=self.config['xtractor'].get(),
            dest='xtractor', help='use xtractor plugin')
        p.add_option('--no-xtractor', action='store_false',
            default=self.config['xtractor'].get(),
            dest='xtractor', help='do not use xtractor plugin')
        p.add_option('--from-title', action='store_true',
            default=self.config['from_title'].get(),
            dest='from_title', help='derive genre from title')
        p.add_option('--no-from-title', action='store_false',
            default=self.config['from_title'].get(),
            dest='from_title', help='do not derive genre from title')
        p.add_option('--parent-genres', action='store_true',
            default=self.config['parent_genres'].get(),
            dest='parent_genres', help="add primary genre's parent genres")
        p.add_option('--no-parent-genres', action='store_false',
            default=self.config['parent_genres'].get(),
            dest='parent_genres', help="do not add primary genre's parent genres")
        p.add_option('--genre', type='string',
            dest='genre', help='specify the genre to assign to the selected items')

        c = Subcommand('autogenre', parser=p, help='derive and assign song genres')
        c.func = self._run_autogenre_cmd
        return [c]

    def _run_autogenre_cmd(self, lib, opts, args):
        self._apply_opts_to_config(opts)
        if opts.genre:
            ok = self._genres().contains(opts.genre)
            assert args, "Must specify selector when --genre provided"
            assert ok, "Provided genre '{}' is not registered within genre tree!".format(opts.genre)
        query = decargs(args)
        parsed_query, parsed_sort = parse_query_parts(query, Item)
        parsed_sort = FixedFieldSort("albumartist", ascending=True)
        items = lib.items(parsed_query, parsed_sort)
        all = opts.all or opts.genre is not None
        force = opts.force or opts.genre is not None
        pretend = self.config['pretend'].get()
        filtered_items = [item for item in items if _filter_item(item, all, force)]
        self._log.info('Selected {} items for genre update...', len(filtered_items))
        # Update items
        for item in filtered_items:
            genre, genres, source = self._item_genre(item, all, force, opts.genre)
            genre_changed = genre != item.get('genre')
            genres_changed = genres != item.get('genres')
            genre_source_changed = source != item.get('genre_source')
            changed = genre_changed or genres_changed or genre_source_changed
            if changed and genres is not None:
                msg = "Change genre from '{}' to '{}' ({}) for item: {}"
                self._log.info(msg, item.get('genre'), genre, source, item)
                if not pretend:
                    item.genre = genre
                    item.genres = genres
                    item.genre_source = source
                    if config['import']['write'].get():
                        item.try_write()
                    item.store()
        # TODO: match remix artist within title and get genre from artist: TITLE (ARTIST remix)
        # Update albums
        album_ids = set([item.album_id for item in filtered_items if item.album_id])
        for album_id in album_ids:
            album = lib.get_album(album_id)
            if album:
                self._update_album_genre(album)

    def _apply_opts_to_config(self, opts):
        for k, v in opts.__dict__.items():
            if v is not None and k in self.config:
                self.config[k] = v

    def _item_genre(self, item, all, force, force_genre=None):
        genres, source = self._item_genres(item, all, force, force_genre)
        genrel = self._str2list(genres)
        genre = genres and genrel[0] or None

        if genres:
            if self.config['parent_genres'].get() and genre:
                # Append primary genre's parent genres to genre list
                parent_genres = self._genres().parents(genre)
                parent_genres = [self._format_genre(g) for g in parent_genres]
                genrel = genrel + [g for g in parent_genres if g not in genrel]
                genres = self._list2str(genrel)

        return genre, genres, source

    def _item_genres(self, item, all, force, force_genre):
        genre = item.get('genres')
        if not genre:
            genre = item.get('genre')
        source = item.get('genre_source')
        if _filter_item(item, all, force):
            if force_genre is not None:
                source = force_genre and 'user' or None
                genre = self._format_genre(force_genre.lower())
            if source != 'user' or not genre:
                # auto-detect genre
                if self.config['lastgenre'].get():
                    genre = self._lastfm_genre(item)
                    if genre is not None:
                        source = 'lastfm'
                if self.config['from_title'].get():
                    genre, matched = self._fix_remix_genre(item, genre)
                    if matched and genre is not None:
                        source = 'title'
                if genre is None and self.config['xtractor'].get():
                    genre = self._essentia_genre(item)
                    if genre is not None:
                        source = 'essentia'
        return genre, source

    def _is_remix(self, title):
        return self._remix_regex.match(title) is not None

    def _lastfm_genre(self, item):
        genre = None
        src = None
        source = self._lastgenre.config['source'].get()
        if self._is_remix(item.get('title')) and source != 'track':
            # When item is remix, get genre frpm the last.fm track.
            # (The artist's genre would be most likely wrong / the original.
            # E.g. 'Fugees - Ready or not (Champion Bootleg)'.
            # For other items the album/artist source is more reliable.)
            self._lastgenre.config['source'] = 'track'
            try:
                genre, src = self._lastgenre._get_genre(item)
            finally:
                self._lastgenre.config['source'].set(source)
        else:
            genre, src = self._lastgenre._get_genre(item)
        if genre:
            msg = "Got last.fm genre '{}' based on {} for item: {}"
            self._log.debug(msg, genre, src, item)
        return genre

    def _fix_remix_genre(self, item, genre):
        '''Match genre within title or album and prepend to genre list.
        This fixes remixes that are wrongly tagged on last.fm'''
        title = item.get('title')
        album = item.get('album')
        genres = self._str2list(genre)
        matched = self._genres().match(title)
        if matched:
            source = 'title'
        elif album:
            source = 'album'
            matched = self._genres().match(album)
        prepend_genre = None
        if matched:
            prepend_genre = matched.lower()
        if prepend_genre:
            prepend_genre = self._format_genre(prepend_genre)
            genres = [g for g in genres if g != prepend_genre]
            genre = self._list2str([prepend_genre] + genres)
            self._log.debug("Fixed genre '{}' based on {} of item: {}", genre, source, item)
            return genre, True
        return genre, False

    def _essentia_genre(self, item):
        if not item.get('bpm') or not item.get('genre_rosamerica'):
            # Run essentia analysis if result not known yet.
            self._log.debug('Analyzing item using essentia: {}', item)
            self._xtractor._run_analysis(item)
        if 'genre_rosamerica' not in item:
            # Essentia analysis may not provide data in some cases.
            return None
        # Use Essentia's mapped genre_rosamerica value
        genre_rosamerica = item.genre_rosamerica
        genre_rosamerica_probability = float(item.genre_rosamerica_probability)
        genre_electronic = item.genre_electronic
        genre_electronic_probability = float(item.genre_electronic_probability)
        genre = ROSAMERICA_GENRES.get(genre_rosamerica)
        genre_electronic_strong = self.config['genre_electronic_strong'].get()
        genre_rosamerica_strong = self.config['genre_rosamerica_strong'].get()
        genre_electronic_prepend = self.config['genre_electronic_prepend'].get()
        genre_electronic_append = self.config['genre_electronic_append'].get()

        if genre == 'dance':
            if genre_electronic_probability > genre_electronic_strong:
                # Use the result of Essentia's electronic genre model
                genre = ELECTRONIC_GENRES.get(genre_electronic)
        elif genre_rosamerica_probability < genre_rosamerica_strong and genre_electronic_probability > genre_electronic_prepend:
            # Prepend electronic to genre list
            genres = ['electronic'] + [genre]
            genre_electro = ELECTRONIC_GENRES.get(genre_electronic)
            if genre_electro: # Append electronic sub genre to list
                genres += [genre_electro]
            genre = self._list2str(genres)

        if genre_electronic_probability > genre_electronic_append:
            if genre_rosamerica in ('rhy', 'pop', 'hip'):
                # Append electronic to genre list
                genres = self._str2list(genre)
                if 'electronic' not in genres:
                    genre = self._list2str(genres + ['electronic'])
            elif genre == 'dance':
                genre = 'electronic'

        genre = self._format_genre(genre)
        self._log.debug("Got essentia genre '{}' for item: {}", genre, item)
        return genre

    def _genres(self):
        if not self._genre_tree:
            genre_tree_file = self._lastgenre_conf.get('canonical')
            if not genre_tree_file:
                genre_tree_file = os.path.join(os.path.dirname(__file__), '..', 'lastgenre', 'genres-tree.yaml')
            genre_wh_file = self._lastgenre_conf.get('whitelist')
            assert genre_wh_file, "Config option lastgenre.whitelist is not specified!"
            with open(genre_wh_file, 'r') as f:
                genre_whitelist = [genre.strip().lower() for genre in f.readlines() if genre.strip()]
            with codecs.open(genre_tree_file, 'r', encoding='utf-8') as f:
                genre_tree_yaml = yaml.safe_load(f)
            self._genre_tree = GenreTree(genre_tree_yaml, genre_whitelist)

        return self._genre_tree

    def _format_genre(self, genre):
        return self._lastgenre._format_tag(genre)

    def _str2list(self, str):
        return str and str.split(self._separator) or []

    def _list2str(self, list):
        return self._separator.join(list)


def _filter_item(item, all, force):
    src = item.get('genre_source')
    empty = not item.get('genre')
    return (empty or src in SOURCES or not src and all) and (empty or force)

def _is_plugin_enabled(plugin_name):
    enabled_plugins = config['plugins'].get() if config['plugins'].exists() else []
    return plugin_name in enabled_plugins

def _most_common(names):
    r = Counter([name for name in names if name]).most_common(1)
    if len(r) == 1:
        return r[0][0]
