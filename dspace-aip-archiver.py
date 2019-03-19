#!/usr/bin/env python3


"""Find new and changed objects in DSpace and export them as Archival Information Packages.
    Uses OAI-PMH to find new and changed objects within specified time range.  Uses Handle identifiers from those
    records to call DSpace AIP export tool.  Serializes AIP packages to specified
    location.

    Configuration file:
    Copy configuration file stub to dspace-aip-archiver.config.local
    Edit to reflect needs.  E.g.:
    [DEFAULT]
    OAI_URL = https://vtechworks.lib.vt.edu/oai/request?
    OAI_REQUEST = request?verb=ListRecords&metadataPrefix=oai_dc&from=
    DAYS = 1
    STORAGE_LOCATION = /tmp/dspace-export
    DSPACE_CLI = /dspace/bin/dspace
    DSPACE_EPERSON = <user>@organization.tld

    This configuration will export all VTechWorks items which have been deposited or changed in the last day
    to a dspace-export directory in /tmp
"""


import configparser
from os import getcwd
from os.path import join
from pathlib import Path
from datetime import datetime, timedelta
from oaipmh.client import Client
from oaipmh.metadata import MetadataRegistry, oai_dc_reader
from subprocess import run


def get_config():
    """Retrieve configuration from ./dspace-aip-archiver.config.local"""
    if Path(join(getcwd(), "dspace-aip-archiver.config.local")).is_file():
        config = configparser.ConfigParser()
        config.read(join(getcwd(), "dspace-aip-archiver.config.local"))
        return config["DEFAULT"]["OAI_URL"], config["DEFAULT"]["OAI_REQUEST"], int(config["DEFAULT"]["DAYS"]), \
               config["DEFAULT"]["STORAGE_LOCATION"], config["DEFAULT"]["DSPACE_CLI"], \
               config["DEFAULT"]["DSPACE_EPERSON"]
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
        if record[1]:
            rec = record[1].getField("identifier")
            ids.append(get_handle(rec))
    return ids


def get_handle(record):
    """Strip out handle ids from list of new and changed records"""
    handleid = ""
    for r in record:
        if "handle" in r:
            handleid = r.replace("http://hdl.handle.net/","")
    return handleid


def export_aip(handle, cli, eperson, storage):
    """Call DSpace CLI to export AIPs to storage_location"""
    eperson = "-e " + eperson
    item = "-i " + handle
    file_name = handle.replace("/", "-") + ".zip"
    destination = join(storage, file_name)
    run([cli, "packager", "-d", "-t AIP", eperson, item, destination])


if __name__ == "__main__":
    oai_url, oai_request, days, storage_location, dspace_cli, dspace_eperson = get_config()
    date = request_date(days)
    records = get_records(oai_url, date)
    ids = get_identifiers(records)
    for id in ids:
        export_aip(id, dspace_cli, dspace_eperson, storage_location)







