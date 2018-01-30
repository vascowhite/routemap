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
        :return:
        :rtype:
        """
        print(Path('.').absolute())
        input_file = './tests/test.bvs'
        output_file = './tests/test.png'

        routemap.plot(
            input_file,
            output=output_file,
            custtitle='Test',
        )

        self.assertTrue(Path(output_file).is_file())


if __name__ == '__main__':
    unittest.main()
