
import csv
import requests

ENDPOINT = 'https://api.scraperwiki.com/api/1.0/datastore/sqlite'

try:
    from gtfsni import get_pkg_data, get_app_data
except ImportError:
    def get_pkg_data(path):
        return os.path.join('data', path)
    get_app_data = get_pkg_data

def CSVReader(schema):
    sql = "SELECT DISTINCT %s FROM `swdata` WHERE operator_id='METRO'"
    sql %= ', '.join(schema)
    params = {
        'name': 'translink_ni_timetables',
        'format': 'csv',
        'query': sql,
    }
    response = requests.get(ENDPOINT, params=params)
    #print response.text
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

SCHEMA_MAP = {
    'routes.txt': ((
        'agency_id', 'route_id', 'route_type', 'route_url',
        'route_short_name', 'route_long_name',
    ),(
        'agency_id', 'route_id', 'route_type', 'route_url',
        'route_short_name', 'route_long_name', 'route_desc', 
        'route_color', 'route_text_color',
    )),
    'trips.txt': ((
    ),(
    'route_id', 'service_id', 'trip_id', 'trip_headsign', 'trip_short_name',
    'direction_id', 'block_id', 'shape_id', 'timeframe_id', 'trip_sequence',
    )),
}

def get_schemas(fname):
    schema_in, schema_out = SCHEMA_MAP[fname]
    assert set(schema_in) <= set(schema_out)
    return schema_in, schema_out

def write_routes():
    fname = 'routes.txt'
    schema_in, schema_out = get_schemas(fname)
    reader = CSVReader(schema_in)
    with CSVWriter(fname, schema_out) as writer:
        for row in reader:
            writer.writerow(**row)

def write_trips_and_calendar(reader, writer1, writer2):
    alltripids = []
    tripsfile = 'trips.txt'
    calendarfile = 'calendar.txt'
    schema_in, trips_schema = get_schemas(tripsfile)
    _, calendar_schema = get_schemas(calendarfile)
    reader = CSVReader(schema_in)
    sortkey = lambda X: (X['agency_id'], X['route_id'])
    data = sorted(reader, key=sortkey)
    services = {}
    for key, g in groupby(data, key=sortkey):
        # g contains one row for every stop on the route but the data
        # we want next - trip number and service id - is the same for
        # each row (in the group), so we just use the first row and continue.
        # the time schedule string should never be jagged for this to work
        # ie. each stop has a value for each trip, even if it is '...'
        agencyid, routeid = key
        row = g.next()
        direction = row['route_direction']
        headsign = row['route_end']
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
            short_name = '%s - %s' % (srvno, headsign)
            for idx, daycode in split_timeframe(timeframe):
                idx = str(idx)
                tripid = make_trip_id(routeid, idx, tripno)
                csvrow = (routeid, service_id, tripid, headsign, short_name,
                        direction, None, None, daycode, tripno)
                writer1.writerow(csvrow)
                alltripids.append(tripid)
                dayname = daycode_to_name[daycode]
                service_calendar[dayname.lower()] = 1 # being set multiple times
    # write 'calendar.txt'
    for k in sorted(services.keys()):
        writer2.writerow(services[k])
    #assert trip_ids are unique
    assert len(alltripids) == len(set(alltripids))

def main():
    write_routes()

