"""
Setup as a package
"""

from setuptools import setup

requires = [
    'pillow',
    'requests',
    'vincenty',
    'basemap'
]

links = [
    "https://github.com/matplotlib/basemap.git",
]

setup(
    name='routemap',
    version='0.1.0',
    author='P White',
    author_email='paul@vascowhite.co.uk',
    packages=['routemap'],
    url='https://github.com/vascowhite/routemap',
    description='Generate route maps from various route file formats',
    entry_points={
        'console_scripts': [
            'routemap = routemap.__main__:main'
        ]
    },
    test_suite="tests",
    install_requires=requires,
    dependency_links=links,
)
