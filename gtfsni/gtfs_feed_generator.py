
import os
import csv
from itertools import groupby
import time
import shutil

import requests

from gtfsni import get_pkg_data, get_app_data
from gtfsni import utils
from gtfsni.generate_metro_stops import main as generate_metro_stops

ENDPOINT = 'https://api.scraperwiki.com/api/1.0/datastore/sqlite'
TRIPDATAJOINER = '|'
TRIPDATAPARTJOINER = '#'
RAW_TIMETABLE_SCHEMA = (
    'agency_id', 'operator_id', 'service_id',
    'route_id', 'route_url', 'route_type', 'route_long_name',
    'route_short_name', 'route_begin', 'route_end', 'route_direction',
    'stop_name', 'stop_sequence', 'schedule',
)
GTFS_SCHEMA_MAP = {
    'stops.txt': [(
        'stop_lat', 'stop_lon', 'stop_name', 'road', 'direction', 'geohash',
    ),(
        'stop_id', 'stop_code', 'stop_name', 'stop_desc', 'stop_lat', 'stop_lon',
        'zone_id', 'stop_url', 'location_type', 'parent_station', 'stop_timezone',
        'road', 'direction', 'geohash',
    )],
    'routes.txt': [(
        'agency_id', 'route_id', 'route_type', 'route_url',
        'route_short_name', 'route_long_name',
    ),(
        'agency_id', 'route_id', 'route_type', 'route_url',
        'route_short_name', 'route_long_name', 'route_desc', 
        'route_color', 'route_text_color',
    )],
    'trips.txt': [
        '*'
    ,(
        'route_id', 'service_id', 'trip_id', 'trip_headsign', 'trip_short_name',
        'direction_id', 'block_id', 'shape_id', 'timeframe_id', 'trip_sequence',
    )],
    'calendar.txt': [
        None
    ,(
        'service_id',
        'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
        'start_date', 'end_date',
    )],
    'stop_times.txt': [
        '*'
    ,(
        'trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence',
        'stop_headsign', 'pickup_type', 'drop_off_type', 'shape_dist_travelled',
    )],
}


def make_id(*args):
    return utils.slugify(' '.join(str(arg) for arg in args))

def make_route_id(*args):
    return make_id(*args).replace('-', '').upper()

def make_trip_id(routeid, timeframeid, tripno):
    return make_id(routeid, timeframeid, '%03d' % int(tripno))

def CSVReader(schema):
    sql = "SELECT %s FROM `swdata` WHERE operator_id='METRO'"
    if schema == '*':
        schema = RAW_TIMETABLE_SCHEMA
        query = ', '.join(schema)
    else:
        query = 'DISTINCT ' + ', '.join(schema)
    sql %= query
    params = {
        'name': 'translink_ni_timetables',
        'format': 'csv',
        'query': sql,
    }
    response = requests.get(ENDPOINT, params=params)
    reader = csv.DictReader(response.text.splitlines(), schema)
    reader.next()
    return sorted(reader, key=lambda row: tuple(row.values()))

class CSVWriter(object):

    def __init__(self, filename, schema):
        self.filename = get_app_data('gtfs/' + filename)
        self.schema = schema
        self._fd = open(self.filename, 'wb')
        self._writer = csv.DictWriter(self._fd, schema)
        self._write_header()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def _write_header(self):
        self._writer.writerow(dict(zip(self.schema, self.schema)))

    def writerow(self, **kw):
        row = dict((field, None) for field in self.schema)
        row.update(kw)
        self._writer.writerow(row)
        return row

    def close(self):
        try:
            self._fd.close()
        except:
            pass

def get_schemas(fname):
    schema_in, schema_out = GTFS_SCHEMA_MAP[fname]
    if schema_in and schema_out and schema_in != '*':
        assert set(schema_in) <= set(schema_out), ', '.join(schema_out)
    return schema_in, schema_out

def write_agency():
    src = get_pkg_data('translink/agency.csv')
    dest = get_app_data('gtfs/agency.txt')
    shutil.copyfile(src, dest)

def write_routes():
    fname = 'routes.txt'
    schema_in, schema_out = get_schemas(fname)
    reader = CSVReader(schema_in)
    with CSVWriter(fname, schema_out) as writer:
        for row in reader:
            writer.writerow(**row)

def write_stops():
    fname = 'stops.txt'
    schema_in, schema_out = get_schemas(fname)
    metro_stops = get_app_data('translink/metro_stops.csv')
    if not os.path.exists(metro_stops):
        raise Exception("stop coordinate file not found - %s" % metro_stops)
    direction2code = utils.direction2code
    with open(metro_stops) as fd:
        reader = csv.DictReader(fd, schema_in)
        reader.next()
        with CSVWriter(fname, schema_out) as writer:
            for row in reader:
                stop, direction = row['stop_name'], row['direction']
                lat, lon = row['stop_lat'], row['stop_lon']
                if not lat or not lon:
                    continue
                id = make_id('translinkni', stop, direction2code[direction])
                writer.writerow(
                    stop_id=id,
                    stop_name=row['stop_name'],
                    stop_lat=row['stop_lat'],
                    stop_lon=row['stop_lon'],
                    stop_desc=row['road'],
                )

def write_trips_and_calendar():
    alltripids = []
    tripsfile = 'trips.txt'
    schema_in, trips_schema = get_schemas(tripsfile)
    reader = CSVReader(schema_in)
    sortkey = lambda X: (X['agency_id'], X['route_id'])
    data = sorted(reader, key=sortkey)
    services = {}
    with CSVWriter(tripsfile, trips_schema) as writer:
        for key, g in groupby(data, key=sortkey):
            # g contains one row for every stop on the route but the data
            # we want next - trip number and service id - is the same for
            # each row (in the group), so we just use the first row and continue.
            # the time schedule string should never be jagged for this to work
            # ie. each stop has a value for each trip, even if it is '...'
            agencyid, routeid = key
            row = g.next()
            direction = row['route_direction']
            route_end = row['route_end']
            tripdata = (tuple(t.split(TRIPDATAPARTJOINER)[:3]) for t in row['schedule'].split(TRIPDATAJOINER) if t)
            service_id = row['service_id']
            # inbound and outbound routes have the same service id
            service_calendar = services.setdefault(service_id, {
                'service_id': service_id,
                'monday': 0,
                'tuesday': 0,
                'wednesday': 0,
                'thursday': 0,
                'friday': 0,
                'saturday': 0,
                'sunday': 0,
                'start_date':'20110101',
                'end_date':'20991231',
            })
            for tripno, srvno, timeframe in tripdata:
                #use numeric timeframe code in trip id
                #tfname, tfweight = get_time_period_name_and_weight(timeframe)
                tripno = int(tripno)
                headsign = '%s - %s' % (srvno, route_end)
                for idx, daycode in utils.split_timeframe(timeframe):
                    idx = str(idx)
                    tripid = make_trip_id(routeid, idx, tripno)
                    writer.writerow(
                        route_id=routeid, service_id=service_id, trip_id=tripid,
                        trip_headsign=headsign, trip_short_name=headsign,
                        direction_id=direction, timeframe_id=daycode,
                        trip_sequence=tripno
                    )
                    alltripids.append(tripid)
                    dayname = utils.daycode_to_name[daycode]
                    service_calendar[dayname.lower()] = 1
    calendarfile = 'calendar.txt'
    _, calendar_schema = get_schemas(calendarfile)
    # write 'calendar.txt'
    with CSVWriter(calendarfile, calendar_schema) as writer:
        for k in sorted(services.keys()):
            writer.writerow(**services[k])
    #assert trip_ids are unique
    assert len(alltripids) == len(set(alltripids))

def write_stop_times():
    fname = 'stop_times.txt'
    schema_in, schema_out = get_schemas(fname)
    reader = CSVReader(schema_in)
    with CSVWriter(fname, schema_out) as writer:
        for row in reader:
            agencyid = row['agency_id']
            routeid = row['route_id']
            stopname = row['stop_name']
            direction = row['route_direction']
            stopid = make_id(agencyid, stopname, direction)
            stopno = row['stop_sequence']
            headsign = '%s %s' % (row['route_short_name'], row['route_end'])
            stoptime_data = (
                tuple(
                    t.split(TRIPDATAPARTJOINER)
                ) for t in row['schedule'].split(TRIPDATAJOINER) if t
            )
            for tripno, srvno, timeframe, time in stoptime_data:
                #ignore any special instruction code for the minute
                if time == '...':
                    #time = None
                    continue
                else:
                    time = '%s:%s:00' % (time[:2], time[2:4])
                for idx, daycode in utils.split_timeframe(timeframe):
                    idx = str(idx)
                    tripid = make_trip_id(routeid, idx, tripno)
                    t = (tripid, time, time, stopid, stopno, stopname, None, None, None)
                    writer.writerow(
                        trip_id=tripid, stop_id=stopid, stop_sequence=stopno,
                        arrival_time=time, departure_time=time,
                        stop_headsign=headsign,
                    )

def compress():
    timestamp = time.strftime('%Y_%m_%d_%H%M%S', time.localtime())
    archive = 'google_transit_translinkni_%s.zip' % timestamp
    cxt = {
        'archive': archive,
        'src': get_app_data('gtfs/'),
        'dest': get_app_data('dist/' + archive),
        'destroot': get_app_data('dist/'),
        'symlink': 'google_transit.zip',
    }
    cmd = (
        'cd %(src)s && zip %(archive)s *.txt && mv %(archive)s %(dest)s'
        ' && cd %(destroot)s && rm -f %(symlink)s'
        ' && ln -s %(archive)s %(symlink)s'
    )
    cmd %= cxt
    ret = os.system(cmd)
    if ret:
        raise OSError(cmd)
    print 'created archive: %s' % cxt['dest']

def main():
    generate_metro_stops()
    write_stops()
    write_routes()
    write_trips_and_calendar()
    write_stop_times()
    write_agency()
    compress()


