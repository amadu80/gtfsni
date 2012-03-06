#!/usr/bin/env python

import os
import sys
import re
import csv

import requests
from geohash import encode as geohash

from gtfsni import get_pkg_data, get_app_data
from gtfsni.utils import slugify, direction2name

FIXES_FILE = get_pkg_data('translink/metro_stops_fixes.csv')

assert os.path.exists(FIXES_FILE), "missing data file - %s" % FIXES_FILE

ENDPOINT = 'https://api.scraperwiki.com/api/1.0/datastore/sqlite'
REFERENCE_SCHEMA = [
    'name', 'road', 'lat', 'lng', 'direction'
]
TIMETABLE_SCHEMA = [
    'stop_name', 'route_direction',
]
STOPS_SCHEMA = [
    'stop_lat', 'stop_lon', 'stop_name', 'road', 'direction', 'geohash'
]
FIXES_SCHEMA = [
    'stop_name', 'route_direction', 'stop_lat', 'stop_lon', 'road',
]
INBOUND_REFERENCE = {}
OUTBOUND_REFERENCE = {}
REFERENCE_STOPS = {}
REFERENCE_STOPS['Inbound'] = REFERENCE_STOPS[1] = INBOUND_REFERENCE
REFERENCE_STOPS['Outbound'] = REFERENCE_STOPS[0] = OUTBOUND_REFERENCE
TIMETABLE_STOPS = None
OPENTRANSLINK_STOPS = {}
FIXES = {}

def ReferenceReader(fd):
    return csv.DictReader(fd, REFERENCE_SCHEMA)

def TimetableReader(fd):
    return csv.DictReader(fd, TIMETABLE_SCHEMA)

def FixesReader(fd):
    return csv.DictReader(fd, FIXES_SCHEMA)

def StopsWriter(fd):
    return csv.DictWriter(fd, STOPS_SCHEMA)

def StopsHeader():
    return dict(zip(STOPS_SCHEMA, STOPS_SCHEMA))

def StopsRow():
    return dict((field, None) for field in STOPS_SCHEMA)

def load_reference_stops():
    sql = "SELECT DISTINCT name, road, lat, lng, direction from `swdata`"
    params = {
        'name': 'translink_metro_stops',
        'format': 'csv',
        'query': sql,
    }
    response = requests.get(ENDPOINT, params=params)
    reader = ReferenceReader(response.text.splitlines())
    reader.next()
    for line in reader:
        # generate variations - all these will give the same lat/lon
        possibilities = [
            slugify(line['name']),
            slugify(line['name'] + ' ' + line['road']),
            slugify(line['road']),
        ]
        try:
            stops = [REFERENCE_STOPS[line['direction']]]
        except KeyError:
            # no direction given - add the stop to both reference dicts
            stops = [REFERENCE_STOPS[0], REFERENCE_STOPS[1]]
        for reference_dict in stops:
            for possibility in possibilities:
                reference_dict[possibility] = (
                    float(line['lat']), float(line['lng']), line['road'],
                )

def load_timetable_stops():
    global TIMETABLE_STOPS
    sql = (
        "SELECT DISTINCT stop_name, route_direction from `swdata`"
        " WHERE operator_id='METRO'"
    )
    params = {
        'name': 'translink_ni_timetables',
        'format': 'csv',
        'query': sql,
    }
    response = requests.get(ENDPOINT, params=params)
    if response.status_code != 200:
        sys.exit("GET '%s' failed. Error: %s" % (response.url, response.error))
    reader = TimetableReader(response.text.splitlines())
    reader.next()
    TIMETABLE_STOPS = [(row['stop_name'], row['route_direction']) for row in reader]

def load_opentranslink_stops():
    with open(get_pkg_data('translink/opentranslink_stops.csv')) as fd:
        reader = csv.reader(fd)
        for row in reader:
            key = slugify(row[0])
            val = (row[1], row[2],'')
            OPENTRANSLINK_STOPS[key] = val

def load_manual_fixes():
    with open(FIXES_FILE) as fd:
        reader = FixesReader(fd)
        reader.next()
        for row in reader:
            key = (row['stop_name'], int(row['route_direction']))
            val = (row['stop_lat'], row['stop_lon'], row['road'])
            FIXES[key] = val


def _find_info(stop, stops, top, tail):
    slug = slugify(stop)
    info = stops.get(slug, None)
    if not info and tail:
        slug = slugify(tail + ' ' + top)
        info = stops.get(slug, None)
    return info

def find_info(stop, direction):
    """
    Heuristic search for the named stop, first try the direction given, then
    the other direction (across the road will be better than nothing), then
    if the stop has more than one part (comma-separated), try the second part
    on its own.
    """
    stops = REFERENCE_STOPS[direction]
    other_stops = REFERENCE_STOPS[int(not direction)]
    top, comma, tail = stop.partition(',')
    info = _find_info(stop, stops, top, tail)
    if not info:
        info = _find_info(stop, other_stops, top, tail)
    if not info and tail:
        info = _find_info(tail, stops, None, None)
        if not info:
            info = _find_info(tail, other_stops, None, None)
    if not info:
        info = _find_info(stop, OPENTRANSLINK_STOPS, None, None)
    if info:
        return info

def main():
    """
    Load the stops and coordinate data as derived from the map view pages to
    the REFERENCE_STOPS dict. Load the stop names as derived from the timetable
    pages to TIMETABLE_STOPS list. Load the manually-added stop coordinates to
    FIXES dict.
    """
    load_reference_stops()
    load_timetable_stops()
    load_opentranslink_stops()
    load_manual_fixes()
    found = missing = 0
    with open(get_app_data('translink/metro_stops.csv'), 'wb') as fd:
        writer = StopsWriter(fd)
        writer.writerow(StopsHeader())
        for name, direction in TIMETABLE_STOPS:
            direction = int(direction) # 0 or 1
            row = StopsRow()
            row['stop_name'] = name
            row['direction'] = direction2name[direction]
            try:
                # has it been added manually?
                info = FIXES[(name, direction)]
            except KeyError:
                # try to find from the google map-scraped coords
                info = find_info(name, direction)
            if info:
                # info is a 3-tuple
                x, y = row['stop_lat'], row['stop_lon'] = info[:2]
                row['road'] = info[2]
                row['geohash'] = geohash(float(x), float(y))
                found += 1
            else:
                print "MISSING: ", name, direction
                missing += 1
            writer.writerow(row)
    print 'found: ', found, ', missing: %s' % missing

if __name__ == '__main__':
    main()

