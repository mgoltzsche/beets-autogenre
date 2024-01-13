import unittest
from beetsplug.autogenre.genretree import GenreTree

class TestGenreMatcher(unittest.TestCase):

    def test_match(self):
        genre_tree = [
            'fancy genre 1',
            {
                'fancy genre 2': [
                    'sub genre',
                    'sub genre 1',
                    'genre alias',
                    {
                        'sub genre 2': [
                            'sub sub genre',
                            'sub sub genre 1',
                            'sub sub genre 2',
                            'sub sub genre 3',
                        ],
                    },
                ],
            },
            {
                'fancy genre 2': {
                    'sub genre 3': [
                        'sub sub genre 4',
                    ],
                },
            },
            {
                'none-whitelisted genre': {
                    'none-whitelisted sub genre': [
                        'none-whitelisted sub sub genre',
                    ],
                },
            },
        ]
        genre_whitelist = [
            'fancy genre 1',
            'sub genre',
            'sub sub genre',
            'fancy genre 2',
            'sub genre 1',
            'sub sub genre 2',
            'sub genre 2',
            # aliases:
            #'genre alias',
            #'sub sub genre 1',
            #'sub sub genre 3',
        ]
        testcases = [
            {
                'name': 'match top level genre',
                'input': 'fake title [fancy genre 1]',
                'expected': 'fancy genre 1',
            },
            {
                'name': 'match top level genre 2',
                'input': 'fake title (fancy genre 1)',
                'expected': 'fancy genre 1',
            },
            {
                'name': 'match top level remix genre',
                'input': 'fake title fancy genre 1 remix',
                'expected': 'fancy genre 1',
            },
            {
                'name': 'match top level genre case insensitive',
                'input': 'fake title [Fancy GENRE 1]',
                'expected': 'fancy genre 1',
            },
            {
                'name': 'match bootleg',
                'input': 'fake title [fancy genre 1 bootleg]',
                'expected': 'fancy genre 1',
            },
            {
                'name': 'match sub genre that is also a parent genre',
                'input': 'fake title (fancy genre 2)',
                'expected': 'fancy genre 2',
            },
            {
                'name': 'match nested sub genre',
                'input': 'title sub sub genre 2 mix',
                'expected': 'sub sub genre 2',
            },
            {
                'name': 'match nested sub genre canonical',
                'input': 'prefix sub sub genre 3 mix',
                'expected': 'sub genre 2',
            },
            {
                'name': 'match genre alias to canonical',
                'input': 'prefix genre alias mix',
                'expected': 'fancy genre 2',
            },
            {
                'name': 'match genre before music keyword',
                'input': 'Fancy Genre 1 Music',
                'expected': 'fancy genre 1',
            },
            {
                'name': 'match genre before music keyword suffix',
                'input': 'prefix Fancy Genre 1 Music suffix',
                'expected': 'fancy genre 1',
            },
            {
                'name': 'return top-level parent genre when no whitelisted matched',
                'input': 'none-whitelisted sub sub genre mix',
                'expected': 'none-whitelisted genre',
            },
            {
                'name': 'do not match genre without brackets and remix suffix',
                'input': 'prefix fancy genre 2',
                'expected': None,
            },
        ]
        testee = GenreTree(genre_tree, genre_whitelist)
        for c in testcases:
            info = "\ntest case '{}' input: {}".format(c['name'], c['input'])
            a = testee.match(c['input'])
            self.assertEqual(a, c['expected'], info)

    def test__parents(self):
        genre_tree = [
            {
                'fancy genre': [
                    'sub genre 1',
                    {
                        'sub genre 2': [
                            'sub sub genre',
                        ],
                    },
                ],
            },
        ]
        genre_whitelist = [
            'fancy genre',
            'sub genre 1',
            'sub genre 2',
            'sub sub genre',
        ]
        testcases = [
            {
                'name': 'sub genre',
                'input': 'sub genre 1',
                'expected': ['sub genre 1', 'fancy genre'],
            },
            {
                'name': 'sub genre key',
                'input': 'sub genre 2',
                'expected': ['sub genre 2', 'fancy genre'],
            },
            {
                'name': 'sub sub genre key with alias parent',
                'input': 'sub sub genre',
                'expected': ['sub sub genre', 'sub genre 2', 'fancy genre'],
            },
        ]
        testee = GenreTree(genre_tree, genre_whitelist)
        for c in testcases:
            info = "\ntest case '{}' input: {}".format(c['name'], c['input'])
            a = testee.parents(c['input'])
            self.assertEqual(a, c['expected'], info)

    def test_is_genre(self):
        genre_tree = [
            {
                'fancy genre': [
                    'sub genre 1',
                    {
                        'sub genre 2': [
                            'sub sub genre',
                        ],
                    },
                ],
            },
        ]
        testcases = [
            {
                'name': 'child',
                'input': 'sub sub genre',
                'parent': 'fancy genre',
                'expected': True,
            },
            {
                'name': 'child2',
                'input': 'sub sub genre',
                'parent': 'sub genre 2',
                'expected': True,
            },
            {
                'name': 'sibling',
                'input': 'sub sub genre',
                'parent': 'sub genre 1',
                'expected': False,
            },
            {
                'name': 'itself',
                'input': 'fancy genre',
                'parent': 'fancy genre',
                'expected': True,
            },
        ]
        testee = GenreTree(genre_tree, [])
        for c in testcases:
            info = "\ntest case '{}' input: {}".format(c['name'], c['input'])
            a = testee.is_genre(c['input'], c['parent'])
            self.assertEqual(a, c['expected'], info)
