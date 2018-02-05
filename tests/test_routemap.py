"""
Tests for routemap package
"""
import json
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from routemap import routemap
from requests import Response


class TestRoutemap(unittest.TestCase):

    @patch('matplotlib.pyplot.savefig')
    def test_CanGenerateMap(self, mock_plot):
        """
        Test an image can be generated
        """
        mock_plot.return_value = MagicMock()

        input_file = './tests/test.bvs'
        output_file = './tests/test.png'

        routemap.plot(
            input_file,
            output=output_file,
            custtitle='Test',
        )

        mock_plot.assert_called_with(
            output_file,
            bbox_inches='tight',
            dpi=600,
            papertype='a3')

    @patch('requests.get')
    def test_can_get_current_position(self, mock_requests):
        mock_requests.return_value = MagicMock(
            spec=Response,
            status_code=200,
            json=MagicMock(return_value={"position": [23.5, -34.25]})
        )
        test_url = 'http://anyurlwilldo.com/position'
        self.assertEqual((23.5, -34.25), routemap.get_current_position(
            test_url))

        test_pos = "23 30.0N 34 15.0W"
        self.assertEqual((23.5, -34.25), routemap.get_current_position(test_pos))

    @patch('requests.get')
    def test_can_get_positions_from_url(self, mock_requests):
        with open('tests/test.json') as jsonf:
            test_positions = json.load(jsonf)

        test_lons = [-79.591, -79.6, -79.613, -79.718, -79.918]
        test_lats = [8.996, 9.005, 9.017, 9.117, 9.209]
        test_annots = [(-79.591, 8.996, 'Start'), (-79.918, 9.209, 'End')]
        mock_requests.return_value = MagicMock(
            spec=Response,
            status_code=200,
            json=MagicMock(return_value=test_positions)
        )

        lons, lats, annots = routemap.parseurl('http://anyurlwilldo.com/positions')

        self.assertEqual(test_lons, lons)
        self.assertEqual(test_lats, lats)
        self.assertEqual(test_annots, annots)


if __name__ == '__main__':
    unittest.main()
