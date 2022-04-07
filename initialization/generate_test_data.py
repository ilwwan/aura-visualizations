import psycopg2
import os
import csv
from influxdb_client import InfluxDBClient, Point
import pyedflib
from datetime import datetime, timedelta

POSTGRES_HOST_URL = os.environ.get("POSTGRES_LOCALHOST")
POSTGRES_DATABASE = os.environ.get("POSTGRES_DATABASE")
POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")

IDB_HOST = "localhost"
IDB_PORT = os.environ.get("INFLUXDB_PORT")
IDB_USERNAME = os.environ.get("INFLUXDB_USERNAME")
IDB_PASSWORD = os.environ.get("INFLUXDB_PASSWORD")
IDB_DATABASE = os.environ.get("INFLUXDB_DATABASE")

EDF_SOURCES = {
    9578: "data/tuh/dev/01_tcp_ar/002/00009578/00009578_s002_t001.edf"
}

DATA = {
    "test_table": [
        {
            "id": 1,
            "name": "test_name",
        },
        {
            "id": 2,
            "name": "test_name2",
        }
    ]
}

def generate_postgresql_data(data):
    """
    Generate data in postgresql
    data: input data {
        table_name: [{column1: value1, column2: value2}, {column1: value1, column2: value2},...]
    }
    """
    conn = open_postgresql_session()
    try:
        with conn.cursor() as curs:
            for table,content in data.items():
                generate_table(curs, table, content)
                conn.commit()
    except Exception as e:
        conn.rollback()
        print(e)
    finally:
        conn.close()


def generate_influxdb_data(edf_files, T_sample=1):
    """
    Generate data in influxdb from edf files
    edf_files: input edf files []
    T_sample: later
    """
    url = f"http://{IDB_HOST}:{IDB_PORT}"
    bucket = f'{IDB_DATABASE}/autogen' # ??
    for patient, file in edf_files.items():
        points = get_points_from_edf(file)
        with InfluxDBClient(url=url, token=f"{IDB_USERNAME}:{IDB_PASSWORD}", org="-") as client:
            with client.write_api() as write_api:
                for p in points:
                    write_api.write(bucket, record=p.to_line_protocol())

def get_points_from_edf(edf_file):
    """
    get influxdb points from edf file
    edf_file: filepath
    """
    r = pyedflib.EdfReader(edf_file)
    points = []
    channel_i = 0
    for channel in r.getSignalLabels():
        T_sample_real = 1/r.getSampleFrequency(channel_i)
        time = r.getStartdatetime()
        for val in r.readSignal(channel_i):
            points.append(Point(f"{edf_file}").tag("channel",f"{channel}").field(f"Tension (uV)", val).time(time))
            time += timedelta(seconds=T_sample_real)
        channel_i += 1
    return points

def open_postgresql_session():
    """
    Open postgresql session
    """
    return psycopg2.connect(host=POSTGRES_HOST_URL, database=POSTGRES_DATABASE, user=POSTGRES_USER, password=POSTGRES_PASSWORD, port=5432)

def generate_table(cursor, table, content):
    """
    Create table in postgresql & fill it
    cursor: cursor
    table: table name
    content: table content
    """
    cursor.execute(f"DROP TABLE IF EXISTS {table}")
    first_row: list = content[0]
    columns_sql = ", ".join((map(lambda column: f"{column} varchar(255)" if type(column) == str else f"{column} integer", first_row.keys())))
    cursor.execute(f"CREATE TABLE {table} ({columns_sql})")
    fill_table(cursor, table, content)

def fill_table(cursor, table, content):
    """
    Fills existing table in postgresql with content 
    cursor: cursor
    table: table name
    content: table content
    """
    for row in content:
        columns_sql = ", ".join((map(lambda column: f"{column}", row.keys())))
        values_sql = ", ".join((map(lambda column: f"'{row[column]}'" if type(row[column]=="str") else f"{row[column]}", row.keys())))
        cursor.execute(f"INSERT INTO {table} ({columns_sql}) VALUES ({values_sql})")

def get_data_from_csv(filepath):
    """
    Not used
    """
    with open(filepath, "r") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader)

def get_data_from_csv_dict(csv_files):
    """
    Not used
    """
    data = {}
    for table, filepath in csv_files.items():
        data[table] = get_data_from_csv(filepath)
    return data


if __name__ == "__main__":
    # data = get_data_from_csv("file.csv")
    # data = get_data_from_csv_dict({"test_table": "file.csv"})
    # generate_postgresql_data(DATA)
    generate_influxdb_data(EDF_SOURCES)