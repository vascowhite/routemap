"""
Test that install works
"""
from pathlib import Path
import unittest

from routemap import routemap


class TestRoutemap(unittest.TestCase):

    def test_CanGenerateMap(self):
        """
        Test an image can be generated
        """

        input_file = './tests/test.bvs'
        output_file = './tests/test.png'

        routemap.plot(
            input_file,
            output=output_file,
            custtitle='Test',
        )

        self.assertTrue(Path(output_file).is_file())

    def test_can_get_current_position(self):
        # Change this to run your tests
        test_url = 'http://wx.mqiv.com/position'
        self.assertEqual((12.045, -61.749), routemap.get_current_position(
            test_url))

        test_pos = "23 30.0N 34 15.0W"
        self.assertEqual((23.5, -34.25), routemap.get_current_position(test_pos))


if __name__ == '__main__':
    unittest.main()
