#!/usr/bin/env python

from setuptools import setup, find_packages


__version__ = '0.0.2'

readme = open("README").read()
changes = open("docs/changes.rst").read()
long_description = readme + "\n\n" + changes


setup(
    name="gtfsni",
    version=__version__,
    author="Jord Flanagan",
    author_email="contact@devopsni.com",
    description="Create a Google Transit Feed from scraped Northern Ireland Transport data.",
    long_description=long_description,
    download_url="http://pypi.python.org/packages/source/g/gtfsni/gtfsni-%s.tar.gz" % __version__,
    packages = find_packages(),
    package_data = {'gtfsni': [
        'data/translink/*.*',
    ]},
    entry_points = {
        "console_scripts": [
          "gtfs_validate = gtfsni.gtfs_feed_validator:main",
          "gtfs_view = gtfsni.gtfs_schedule_viewer:main",
          "generate_metro_stops = gtfsni.generate_metro_stops:main",
        ]
    }
)

