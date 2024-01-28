import codecs
import mediafile
import os
import re
import yaml
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
    'dan': 'dance',
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
        'genre_primary': types.STRING,
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
        self._remix_regex = re.compile(r'.+[^\w](remix|bootleg)', re.IGNORECASE)

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
        genre_tree_file = self._lastgenre_conf.get('canonical')
        if not genre_tree_file:
            genre_tree_file = os.path.join(os.path.dirname(__file__), '..', 'lastgenre', 'genres-tree.yaml')
        genre_wh_file = self._lastgenre_conf.get('whitelist')
        assert genre_wh_file, "Config option lastgenre.whitelist is not specified!"
        with open(genre_wh_file, 'r') as f:
            genre_whitelist = [genre.strip().lower() for genre in f.readlines() if genre.strip()]
        with codecs.open(genre_tree_file, 'r', encoding='utf-8') as f:
            genre_tree_yaml = yaml.safe_load(f)
        genre_tree = GenreTree(genre_tree_yaml, genre_whitelist)
        if opts.genre:
            ok = genre_tree.contains(opts.genre)
            assert args, "Must specify selector when --genre provided"
            assert ok, "Provided genre '{}' is not registered within genre tree!".format(opts.genre)
        query = decargs(args)
        parsed_query, parsed_sort = parse_query_parts(query, Item)
        parsed_sort = FixedFieldSort("albumartist", ascending=True)
        items = lib.items(parsed_query, parsed_sort)
        all = opts.all or opts.genre is not None
        force = opts.force or opts.genre is not None
        filtered_items = [item for item in items if _filter_item(item, all, force)]
        print('[autogenre] Selected {} items for genre update...'.format(len(filtered_items)))
        for item in items:
            genre = item.get('genre')
            source = item.get('genre_source')
            genre_primary = item.get('genre_primary')
            if _filter_item(item, all, force):
                if opts.genre is not None:
                    source = opts.genre and 'user' or None
                    genre = self._format_genre(opts.genre.lower())
                    msg = "[autogenre] Setting genre '{}' for item: {}"
                    print(msg.format(genre, item))
                elif source == 'user' and genre_primary:
                    if not genre:
                        genre = genre_primary
                if source != 'user' or not genre:
                    # auto-detect genre
                    if opts.lastgenre:
                        genre = self._lastfm_genre(item)
                        if genre is not None:
                            source = 'lastfm'
                    if genre is None and opts.xtractor:
                        genre = self._essentia_genre(item)
                        if genre is not None:
                            source = 'essentia'
                    if opts.from_title:
                        genre, matched = self._fix_remix_genre(item, genre, genre_tree)
                        if matched and genre is not None:
                            source = 'title'

            if genre:
                genre_primary = genre and self._str2list(genre)[0] or None
                if opts.parent_genres and genre_primary:
                    parent_genres = genre_tree.parents(genre_primary)
                    parent_genres = [self._format_genre(g) for g in parent_genres]
                    genres = self._str2list(genre)
                    genres = genres + [g for g in parent_genres if g not in genres]
                    genre = self._list2str(genres)

            genre_changed = genre != item.get('genre')
            genre_primary_changed = genre_primary != item.get('genre_primary')
            genre_source_changed = source != item.get('genre_source')
            changed = genre_changed or genre_primary_changed or genre_source_changed
            if changed and genre is not None and not opts.pretend:
                item.genre = genre
                item.genre_primary = genre_primary
                item.genre_source = source
                item.store()
        # TODO: match remix artist within title and get genre from artist: TITLE (ARTIST remix)

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
            msg = "[autogenre] Got last.fm genre '{}' based on {} for item: {}"
            print(msg.format(genre, src, item))
        return genre

    def _fix_remix_genre(self, item, genre, genre_tree):
        '''Match genre within title or album and prepend to genre list.
        This fixes remixes that are wrongly tagged on last.fm'''
        title = item.get('title')
        album = item.get('album')
        genres = self._str2list(genre)
        matched = genre_tree.match(title)
        if matched:
            source = 'title'
        elif album:
            source = 'album'
            matched = genre_tree.match(album)
        prepend_genre = None
        if matched:
            prepend_genre = matched.lower()
        if prepend_genre:
            prepend_genre = self._format_genre(prepend_genre)
            genres = [g for g in genres if g != prepend_genre]
            genre = self._list2str([prepend_genre] + genres)
            print("[autogenre] Fixed genre '{}' based on {} of item: {}".format(genre, source, item))
            return genre, True
        return genre, False

    def _essentia_genre(self, item):
        if not item.get('bpm'): # run essentia analysis if result not known yet
            print('[autogenre] Analyzing item using essentia: {}'.format(item))
            self._xtractor._run_analysis(item)
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
        msg = "[autogenre] Got essentia genre '{}' for item: {}"
        print(msg.format(genre, item))
        return genre

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
