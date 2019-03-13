#!/usr/bin/env python3


"""Find new and changed objects in DSpace and export them as Archival Information Packages.
    Uses OAI-PMH to find new and changed objects within specified time range.  Uses Handle identifiers from those
    records to call DSpace AIP export tool.  Serializes AIP packages to specified
    location.

    TODO: Should use REST API when available.
"""


import configparser
from os import getcwd
from os.path import join
from pathlib import Path
from datetime import datetime, timedelta
from oaipmh.client import Client
from oaipmh.metadata import MetadataRegistry, oai_dc_reader


def get_config():
    """Retrieve configuration from ./dspace-aip-archiver.config.local"""
    if Path(join(getcwd(), "dspace-aip-archiver.config.local")).is_file():
        config = configparser.ConfigParser()
        config.read(join(getcwd(), "dspace-aip-archiver.config.local"))
        return config["DEFAULT"]["OAI_URL"], config["DEFAULT"]["OAI_REQUEST"], int(config["DEFAULT"]["DAYS"]), \
               config["DEFAULT"]["STORAGE_LOCATION"]
    else:
        print("Did not find {}".format(join(getcwd(), "dspace-aip-archiver.config.local")))
        exit()


def request_date(day_count):
    """Return period begin date in YYYY-MM-DD"""
    from_date = datetime.now() - timedelta(days=day_count)
    return from_date


def get_records(url, from_date):
    """Retrieve OAI metadata record headers from DSpace"""
    registry = MetadataRegistry()
    registry.registerReader('oai_dc', oai_dc_reader)
    client = Client(url, registry)
    records = client.listRecords(metadataPrefix="oai_dc", from_=from_date)
    return records


def get_identifiers(records):
    """Return DSpace item identifiers"""
    ids = []
    for record in records:
        print(record[1].getField("identifier"))  # TODO: Not complete.  Get handles.


if __name__ == "__main__":
    oai_url, oai_request, days, storage_location = get_config()
    date = request_date(days)
    records = get_records(oai_url, date)
    get_identifiers(records)






