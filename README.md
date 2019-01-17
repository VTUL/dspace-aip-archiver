# dspace AIP archiver

## This is a list of all AIP exports from dspace with the following command - 
`JAVA_OPTS="-Xmx4096m -XX:-UseGCOverheadLimit" /dspace/bin/dspace packager -d -a -t AIP -e zoto@vt.edu -i 10919/0 /tempvtw/all/all.zip`

Further runs will be done with - 
`JAVA_OPTS="-Xmx4096m -XX:-UseGCOverheadLimit" /dspace/bin/dspace packager -o updatedAfter=2019-01-01T00:00:00 -d -a -t AIP -e zoto@vt.edu -i 10919/0 /tempvtw/all/all.zip`

Where updatedafter includes a date of about a week back.  