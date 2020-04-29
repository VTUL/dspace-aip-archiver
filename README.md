# DSpace AIP archiver

This program fetches items that have been created or changed in
defined time period from DSpace using OAI-PMH protocol, creates an APTrust Bagit file for each exported Archival Information Package (AIP), and uploads files to the designated S3 bucket.

- [DSpace AIP archiver](#dspace-aip-archiver)
  - [Installation](#installation)
  - [Run the program](#run-the-program)
  - [Configuration file](#configuration-file)
  - [Sqlite Database](#sqlite-database)
  - [APTrust Bagit structure](#aptrust-bagit-structure)
  - [License](#license)


## Installation

```
git clone git@github.com:VTUL/dspace-aip-archiver.git
cd dspace-aip-archiver
./Makefile
cp dspace-aip-archiver.config dspace-aip-archiver.config.yaml
```

Note: Edit the configuration file dspace-aip-archiver.config.yaml before you run the [dspace_aip_archiver.py](dspace_aip_archiver.py) program.

Create a Sqlite table
```
python createTable.py
```

## Run the program

Run this program [dspace_aip_archiver.py](dspace_aip_archiver.py) in the same server as DSpace installed and put the dspace-aip-archiver.config.yaml file in the same directory as script is located.

## Configuration file

Example
```
aptrust:
  organization: "Virginia Tech Libraries"
  access_level: "Institution"
  storage_option: "Standard"
  group_id: "group_id"
  desc: "DSpace"

dspace:
  OAI_URL: "https://oaiserver/oai/request?"
  OAI_REQUEST: "request?verb=ListRecords&metadataPrefix=oai_dc&from="
  DAYS: 1
  EXPORT_LOCATION: "/temp/dspace-export/"
  STORAGE_LOCATION: "/temp/dspace-storage/"
  DSPACE_CLI: "/dspace/bin/dspace"
  DSPACE_EPERSON: "dspace_user@vt.edu"

s3:
  bucket_name: "dspace-aip-test"

db:
  FileName: "dspace.db"

logs:
  FileName: "dspace_s3_upload.log"
  Level: 20 #INFO

noid:
  NOID_Template: "noid_template"

```

This configuration will export all DSpace items which have been deposited or changed in the last day to a dspace-export directory in /tmp/dspace-export/ and upload APTrust Bagit file to S3 ```dspace-aip-test``` bucket 

## Sqlite Database
This program stores handle, noid, and harvest date information in a Sqlite database

```
CREATE TABLE handle (
      handle text PRIMARY KEY,
      noid text,
      modify_date text
);
```

Example record
```
10919/84424|wv21fc6h|2020-04-29T11:32:37
```

## APTrust Bagit structure

```
<base directory>/
|   aptrust-info.txt
|   bag-info.txt
|   bagit.txt
|   manifest-md5.txt
|   manifest-sha256.txt
|   tagmanifest-md5.txt
|   tagmanifest-sha256.txt
\--- data/
      |   [payload files] <handle>.tar
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details
