import unittest
from beetsplug.autogenre import _most_common

class TestMostCommon(unittest.TestCase):

    def test_most_common(self):
        testcases = [
            {
                'name': 'empty',
                'input': [],
                'expected': None,
            },
            {
                'name': 'single',
                'input': ['genre 1'],
                'expected': 'genre 1',
            },
            {
                'name': 'first',
                'input': ['genre 1', 'genre 2', 'genre 3'],
                'expected': 'genre 1',
            },
            {
                'name': 'first not none',
                'input': [None, 'genre 1', 'genre 2', 'genre 3'],
                'expected': 'genre 1',
            },
            {
                'name': 'most common',
                'input': ['genre 1', 'genre 2', 'genre 2', 'genre 3'],
                'expected': 'genre 2',
            },
            {
                'name': 'first most common',
                'input': ['genre 1', 'genre 2', 'genre 2', 'genre 3', 'genre 3'],
                'expected': 'genre 2',
            },
        ]
        for c in testcases:
            info = "\ntest case '{}' input: {}".format(c['name'], c['input'])
            a = _most_common(c['input'])
            self.assertEqual(a, c['expected'], info)
