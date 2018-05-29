"""
Setup as a package
"""
import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

requires = [
    'numpy',
    'matplotlib',
    'Pillow',
    'requests',
    'vincenty',
    'geographiclib'
]

packages = ['routemap']

about = {}
with open(os.path.join(here, 'routemap', '__version__.py')) as f:
    exec(f.read(), about)

with open('readme.rst') as f:
    readme = f.read()


setup(
    name=about['__title__'],
    version=about['__version__'],
    description=about['__description__'],
    long_description=readme,
    author=about['__author__'],
    author_email=about['__author_email__'],
    url=about['__url__'],
    license=about['__license__'],
    entry_points={
        'console_scripts': [
            'routemap = routemap.__main__:main'
        ]
    },
    test_suite="tests",
    package_dir={'routemap': 'routemap'},
    install_requires=requires,
    packages=packages
)
