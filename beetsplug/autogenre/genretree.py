import re
import sys

class GenreTree:
    def __init__(self, genre_tree, genre_whitelist):
        self._parentmap = _tree2parentmap(genre_tree)
        self._whitelist = set(genre_whitelist)
        self._genres = set(_tree2list(genre_tree))
        genres = sorted(self._genres, key=lambda g: sys.maxsize-len(g))
        genre_regex = '|'.join([re.escape(genre) for genre in genres])
        regex = r'.*?((\[|\()({0})(\)|\])|({0}) +((re)?mix|set|bootleg|music)([^\w]|$))'
        regex = regex.format(genre_regex)
        self._regex = re.compile(regex, re.IGNORECASE)

    def contains(self, genre):
        return genre.lower() in self._genres

    def match(self, title):
        m = self._regex.match(title)
        return m and self._canonicalize(m.group(3) or m.group(5)) or None

    def parents(self, genre):
        genre = genre.lower()
        parent = self._parentmap.get(genre)
        return parent and [genre] + self.parents(parent) or [genre]

    def is_genre(self, genre, parent):
        genre = genre.lower()
        if genre == parent.lower():
            return True
        p = self._parentmap.get(genre)
        return p and self.is_genre(p, parent) or False

    def _canonicalize(self, genre):
        genre = genre.lower()
        if genre in self._whitelist:
            return genre
        parent = self._parentmap.get(genre)
        return parent and self._canonicalize(parent) or genre

def _tree2parentmap(tree, r={}, parent=None):
    if isinstance(tree, str):
        r[tree.lower()] = parent
    elif isinstance(tree, dict):
        for k in tree.keys():
            _tree2parentmap(k, r, parent)
            _tree2parentmap(tree[k], r, k)
    elif isinstance(tree, list):
        for entry in tree:
            _tree2parentmap(entry, r, parent)
    return r

def _tree2list(tree):
    if isinstance(tree, str):
        return [tree]
    elif isinstance(tree, dict):
        return [x for k in tree.keys() for x in [k]+_tree2list(tree[k])]
    elif isinstance(tree, list):
        return [x for entry in tree for x in _tree2list(entry)]
