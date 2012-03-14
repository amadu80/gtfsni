#!/usr/bin/env python

from setuptools import setup, find_packages


__version__ = '0.0.4'

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
          "gtfs_generate = gtfsni.gtfs_feed_generator:main",
          "gtfs_validate = gtfsni.gtfs_feed_validator:main",
          "gtfs_view = gtfsni.gtfs_schedule_viewer:main",
          "gtfs_to_kml = gtfsni.kmlwriter:main",
          "generate_metro_stops = gtfsni.generate_metro_stops:main",
        ]
    }
)

