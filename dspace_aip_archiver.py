#!/usr/bin/env python3
import bagit
import boto3
import configparser
import logging
import os
import shutil
import sqlite3
import sys
import tarfile
import threading
import yaml

from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from noid.pynoid import mint
from oaipmh.client import Client
from oaipmh.metadata import MetadataRegistry, oai_dc_reader
from os import getcwd
from os.path import join
from pathlib import Path
from sqlite3 import Error
from subprocess import run
from time import strftime
from zipfile import ZipFile


class ProgressPercentage(object):

    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)" % (
                    self._filename, self._seen_so_far, self._size,
                    percentage))
            sys.stdout.flush()


def getConfigData():

    if Path(join(getcwd(), "dspace-aip-archiver.config.yaml")).is_file():
        configData = yaml.safe_load(open("dspace-aip-archiver.config.yaml"))
        return configData

    else:
        print(
            "Did not find {}".format(
                join(
                    getcwd(),
                    "dspace-aip-archiver.config.yaml")))
        exit()


def initializeLogConfig(logFileName, logLevel):

    logging.basicConfig(
        filename=logFileName,
        format='%(asctime)s %(levelname)s:%(message)s',
        level=logLevel)


def getDateFromDay(days):

    from_date = datetime.now() - timedelta(days=days)
    return from_date


def getOAIRecordsFromDSpace(configData):

    records = None

    try:
        registry = MetadataRegistry()
        registry.registerReader('oai_dc', oai_dc_reader)
        client = Client(configData["dspace"]["OAI_URL"], registry)
        from_date = getDateFromDay(configData["dspace"]["DAYS"])
        until_date = getDateFromDay(configData["dspace"]["UNTIL"])
        records = client.listRecords(metadataPrefix="oai_dc",from_=from_date,until=until_date)
    except Exception as e:
        print(e)

    return records


def getRecordsWithValues(oaiRecords):

    records = []

    for record in oaiRecords:
        if len(record) > 1 and record[1]:
            records.append(record[1])

    return records


def exportAipFromDSpaceToStorageFolder(handle, configData):

    cli = configData["dspace"]["DSPACE_CLI"]
    eperson = configData["dspace"]["DSPACE_EPERSON"]
    item = handle
    file_name = handle.replace("/", "-") + ".zip"
    destination = join(configData["dspace"]["EXPORT_LOCATION"], file_name)
    run([cli, "packager", "-d", "-t", "AIP", "-e", eperson, "-i", item, destination])


def unZipFile(fileName, sourceFilePath):

    with ZipFile(sourceFilePath + "/" + fileName, 'r') as zipObj:
        zipObj.extractall(sourceFilePath + "/temp/")

    os.remove(sourceFilePath + "/" + fileName)


def getHandleId(record):

    handleid = ""
    for r in record:
        if "hdl.handle.net" in r:
            handleid = r.replace("http://hdl.handle.net/", "")
    return handleid


def createBagitInfo(configData, noid, fileCount):

    bagitInfo = {}
    bagitInfo['Bag-Group-Identifier'] = configData["aptrust"]["group_id"]
    bagitInfo['Internal-Sender-Description'] = configData["aptrust"]["desc"]
    bagitInfo['Source-Organization'] = configData["aptrust"]["organization"]
    bagitInfo['Internal-Sender-Identifier'] = noid
    bagitInfo['Bag-Count'] = str(fileCount[0]) + " of " + str(fileCount[1])
    bagitInfo['Bagging-Date'] = strftime("%Y-%m-%d")

    return bagitInfo


def createAPTrustInfo(configData, bagTitle, bagDesc):

    aptrustInfo = "Title: {0}\nDescription: {1}\nAccess: {2}\nStorage-Option: {3}\n".format(
        bagTitle,
        bagDesc,
        configData["aptrust"]["access_level"].capitalize(),
        configData["aptrust"]["storage_option"])

    return aptrustInfo


def getNoid(noid_template):

    return mint(template=noid_template, n=None, scheme='', naa='')


def createDBConnection(db_file):

    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)

    return conn


def executeDBModifyQuery(conn, sqlStatement, modifyData):

    try:
        cur = conn.cursor()
        cur.execute(sqlStatement, modifyData)
        conn.commit()
        cur.close()
    except Error as e:
        print(e)


def createInsertSQL(handle, noid):

    modify_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    modifyData = (handle, noid, modify_date)

    sql = '''INSERT INTO handle(handle, noid, modify_date) VALUES(?,?,?)'''

    return sql, modifyData


def insertHandle(conn, handle, noid):

    sql, insertData = createInsertSQL(handle, noid)
    executeDBModifyQuery(conn, sql, insertData)


def createUpdateSQL(handle):

    modify_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    modifyData = (modify_date, handle)

    sql = '''UPDATE handle SET modify_date = ? WHERE handle = ?'''

    return sql, modifyData


def updateHandleModifyDate(conn, handle):

    sql, updateData = createUpdateSQL(handle)
    executeDBModifyQuery(conn, sql, updateData)


def searchNoid(conn, handle):

    sql = "SELECT noid FROM handle WHERE handle = ?"
    noid = None
    queryData = (handle,)

    try:
        cur = conn.cursor()
        cur.execute(sql, queryData)
        rows = cur.fetchall()
        for row in rows:
            noid = row[0]
        cur.close()
    except Error as e:
        print(e)

    return noid


def getNoidFromDB(conn, handle, noid_template):

    noid = searchNoid(conn, handle)

    if noid:
        return noid
    else:
        noid = getNoid(noid_template)
        insertHandle(conn, handle, noid)
        return noid


def getValueFromField(recordData, type):

    content = ""
    if len(recordData.getField(type)) > 0 and recordData.getField(type)[0]:
        content = recordData.getField(type)[0]

    return content


def createBagit(sourceFilePath, bagitInfo, checksum):

    bagit.make_bag(sourceFilePath, bagitInfo, checksum=checksum)


def saveToTargetFile(fileName, content, path):

    with open(path + fileName, 'w') as file:
        file.write(content)


def createTarFile(fileName, sourceFilePath, targetFilePath):

    allItem = os.listdir(sourceFilePath)
    with tarfile.open(os.path.join(targetFilePath, fileName), 'w:gz') as tar:
        for item in allItem:
            tar.add(sourceFilePath + item, arcname=item)


def uploadFileToS3(filePath, bucketName, fileName):

    s3.upload_file(
        filePath, bucketName, fileName,
        Callback=ProgressPercentage(filePath)
    )


def initializeLogConfig(logFileName, logLevel):

    logging.basicConfig(
        filename=logFileName,
        format='%(asctime)s %(levelname)s:%(message)s',
        level=logLevel)


def cleanFolder(folderPath):

    if len(folderPath) < 2:
        raise Exception('Please check the folder path in the config file')

    for root, dirs, files in os.walk(folderPath):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))


if __name__ == "__main__":

    configData = getConfigData()

    initializeLogConfig(
        configData["logs"]["FileName"],
        configData["logs"]["Level"])

    export_location = configData["dspace"]["EXPORT_LOCATION"]
    storage_location = configData["dspace"]["STORAGE_LOCATION"]
    noid_template = configData["noid"]["NOID_Template"]

    s3 = boto3.client('s3')
    conn = createDBConnection(configData["db"]["FileName"])

    logging.info("Start harvesting records from VTechWork: %s",
                 datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
    oaiRecords = getOAIRecordsFromDSpace(configData)

    if not oaiRecords:
        logging.info("No changed records from DSpace")
        exit()

    records = getRecordsWithValues(oaiRecords)
    checksum = ["md5", "sha256"]

    for record in records:
        try:
            title = getValueFromField(record, "title")
            desc = getValueFromField(record, "description")
            identifier = getHandleId(record.getField("identifier"))
            dspaceExportFileName = identifier.replace("/", "-") + ".zip"
            bagitFileName = identifier.replace("/", "-") + ".tar"
            logging.info(
                "Handle %s: Start export handle file and create APTrust bagit",
                identifier)
            exportAipFromDSpaceToStorageFolder(
                identifier,
                configData)
            if os.path.exists(export_location + dspaceExportFileName):
                unZipFile(dspaceExportFileName, export_location)
                createTarFile(
                    bagitFileName,
                    export_location +
                    "/temp/",
                    export_location)
                cleanFolder(export_location + "/temp/")
                os.rmdir(export_location + "/temp/")
                noid = getNoidFromDB(conn, identifier, noid_template)
                fileCount = [1, 1]
                bagitInfo = createBagitInfo(configData, noid, fileCount)
                aptrustInfo = createAPTrustInfo(configData, title, desc)
                createBagit(export_location, bagitInfo, checksum)
                saveToTargetFile(
                    "aptrust-info.txt",
                    aptrustInfo,
                    export_location)
                createTarFile(
                    bagitFileName,
                    export_location,
                    storage_location)
                uploadFileToS3(
                    storage_location + bagitFileName,
                    configData["s3"]["bucket_name"], configData["s3"]["folder_name"] + bagitFileName)
                updateHandleModifyDate(conn, identifier)
                cleanFolder(export_location)
                cleanFolder(storage_location)
                logging.info(
                    "Handle %s: APTrust bagit exported to storage",
                    identifier)
        except Exception as e:
            print(e)
            logging.exception(e)
            continue
        else:
            logging.info("Handle %s file not found", dspaceExportFileName)

    conn.close()

    logging.info("Finish harvesting records from VTechWork: %s",
                 datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
