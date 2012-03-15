#!/usr/bin/env python

from setuptools import setup, find_packages


__version__ = '0.0.5'

readme = open("README").read()
changes = open("docs/changes.rst").read()
long_description = readme + "\n\n" + changes


setup(
    name="gtfsni",
    version=__version__,
    author="Jord Flanagan",
    author_email="contact@devopsni.com",
    description="Unofficial Google Transit Feed Generator for Northern Ireland.",
    long_description=long_description,
    url="https://github.com/devopsni/gtfsni",
    download_url="http://pypi.python.org/packages/source/g/gtfsni/gtfsni-%s.tar.gz" % __version__,
    packages = find_packages(),
    package_data = {'gtfsni': [
        'data/translink/*.*',
    ]},
    entry_points = {
        "console_scripts": [
          "gtfsni-generate = gtfsni.gtfs_feed_generator:main",
          "gtfsni-validate = gtfsni.gtfs_feed_validator:main",
          "gtfsni-view = gtfsni.gtfs_schedule_viewer:main",
          "gtfsni-to-kml = gtfsni.kmlwriter:main",
        ]
    }
)

