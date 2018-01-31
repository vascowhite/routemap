"""
Test that install works
"""
from pathlib import Path
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from routemap import routemap
from requests import Response


class TestRoutemap(unittest.TestCase):

    def setUp(self):
        self.mock_requests = MagicMock()

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
        test_url = 'http://127.0.0.1/tests/position.json'
        self.assertEqual((23.5, -34.25), routemap.get_current_position(
            test_url))

        test_pos = "23 30.0N 34 15.0W"
        self.assertEqual((23.5, -34.25), routemap.get_current_position(test_pos))


if __name__ == '__main__':
    unittest.main()
