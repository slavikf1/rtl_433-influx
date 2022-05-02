#!/usr/bin/env python

"""InfluxDB monitoring relay for rtl_433."""

# Start rtl_433 (rtl_433 -F syslog::1433), then this script

# Option: PEP 3143 - Standard daemon process library
# (use Python 3.x or pip install python-daemon)
# import daemon

from __future__ import print_function
from __future__ import with_statement

from influxdb import InfluxDBClient
import socket
from datetime import datetime
import json
import sys
import logging
from systemd import journal

log = logging.getLogger('weatherService')
log.addHandler(journal.JournaldLogHandler())
log.setLevel(logging.INFO)

UDP_IP = "localhost"
UDP_PORT = 1433
INFLUXDB_HOST = "192.168.88.159"
INFLUXDB_PORT = 8086
INFLUXDB_USERNAME = ""
INFLUXDB_PASSWORD = ""
INFLUXDB_DATABASE = ""

TAGS = [
    "26737",
]

FIELDS = [

    "temperature_C",
    "humidity",
    "light_klx",
    "rain_mm",
    "wind_avg_m_s",
    "wind_dir_deg",
    "wind_max_m_s"
    
]

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.bind((UDP_IP, UDP_PORT))


def sanitize(text):
    return text.replace(" ", "_").replace("/", "_").replace(".", "_").replace("&", "")


def parse_syslog(line):
    """Try to extract the payload from a syslog line."""
    line = line.decode("ascii")  # also UTF-8 if BOM
    if line.startswith("<"):
        # fields should be "<PRI>VER", timestamp, hostname, command, pid, mid, sdata, payload
        fields = line.split(None, 7)
        line = fields[-1]
    return line


def rtl_433_probe():
    client = InfluxDBClient(host=INFLUXDB_HOST, port=INFLUXDB_PORT,
                            username=INFLUXDB_USERNAME, password=INFLUXDB_PASSWORD,
                            database=INFLUXDB_DATABASE)

    while True:
        line, _addr = sock.recvfrom(1024)

        try:
            line = parse_syslog(line)

            data = json.loads(line)

            if not "model" in data:
               log.info("skipped data point")
               continue
        
            measurement = sanitize(data['model'])
   
            
            tags = {}
            for tag in TAGS:
                if tag in data:
                    tags[tag] = data[tag]

            fields = {}
            for field in FIELDS:
                if field in data:
                    fields[field] = float(data[field])

            if len(fields) == 0:
                continue

            
            point = {
                "measurement": measurement,
                "time": datetime.utcnow().isoformat(),
                "tags": tags,
                "fields": fields,
            }
            print(point)
            
            try:
                client.write_points([point])
                log.info('Point written: {}'.format(point['time']))
            except Exception as e:
                print("error {} writing {}".format(e, point), file=sys.stderr)

        except KeyError:
            pass

        except ValueError:
            pass


def run():
    # with daemon.DaemonContext(files_preserve=[sock]):
    #  detach_process=True
    #  uid
    #  gid
    #  working_directory
    rtl_433_probe()


if __name__ == "__main__":
    run()
