import unittest

import fluteline

from deep_disfluency.asr.ibm_watson import IBMWatsonAdapter


class TestIBMWatson(unittest.TestCase):

    def setUp(self):
        self.adapter = IBMWatsonAdapter()
        self.adapter.output = fluteline.Queue()
        self.adapter.start()

    def tearDown(self):
        self.adapter.stop()

    def test_adapter(self):

        input_ = [
            # First new
            [
                ('hello', 0, 1),
            ],
            # Old and add new
            [
                ('hello', 0, 1),
                ('my', 1, 2),
            ],
            # Updating old timestamp and add new
            [
                ('hello', 0.5, 1),
                ('my', 1, 2),
                ('name', 3, 4),
            ],
            # Updating old word
            [
                ('hello', 0.5, 1),
                ('your', 1, 2),
                ('name', 3, 4),
            ],
            # Multiple old and new ones with timestamp overlap
            [
                ('once', 3.4, 4),
                ('upon', 4.2, 4.6),
                ('on', 4.3, 4.8),
            ]
        ]

        expected_output = [
            ('hello', 0),
            ('my', 1),
            ('hello', 0),
            ('my', 1),
            ('name', 2),
            ('your', 1),
            ('name', 2),
            ('once', 2),
            ('upon', 3),
            ('on', 3),
        ]

        for update in input_:
            data = {
                'result_index': 0,
                'results': [{'alternatives': [{'timestamps': update}]}]
            }
            self.adapter.input.put(data)

        for word, id_ in expected_output:
            result = self.adapter.output.get()
            self.assertEqual(result['word'], word)
            self.assertEqual(result['id'], id_)


if __name__ == '__main__':
    unittest.main()
