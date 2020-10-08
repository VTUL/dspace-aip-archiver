import os
import tarfile
import tempfile
import zipfile

from dspace_aip_archiver import *
from unittest import TestCase


class TestSuite(TestCase):

    def test_getHandleId(self):

        record = ['AR200304.pdf', 'http://hdl.handle.net/10919/8147']

        output = getHandleId(record)
        expected = "10919/8147"

        self.assertEqual(output, expected)

    def test_createBagitInfo(self):

        testConfigData = {
            'aptrust': {
                'organization': 'VT',
                'group_id': '12345',
                'desc': 'Desc'}}
        testNoid = "zxcvb"
        testfileCount = [1, 1]

        output = createBagitInfo(testConfigData, testNoid, testfileCount)

        self.assertEqual(output["Source-Organization"], "VT")
        self.assertEqual(output["Internal-Sender-Description"], "Desc")
        self.assertEqual(output["Internal-Sender-Identifier"], "zxcvb")
        self.assertEqual(output["Bag-Group-Identifier"], "12345")
        self.assertEqual(output["Bag-Count"], "1 of 1")

    def test_createAPTrustInfo(self):

        testConfigData = {
            'aptrust': {
                'access_level': 'Institution',
                'storage_option': 'Standard'}}
        testTitle = "Title"
        testDesc = "Desc"

        expected = "Title: Title\nDescription: Desc\nAccess: Institution\nStorage-Option: Standard\n"
        output = createAPTrustInfo(testConfigData, testTitle, testDesc)

        self.assertEqual(output, expected)

    def test_createInsertSQL(self):

        testHandle = "1910/2020"
        testNoid = "zxcvb"
        expectedSQL = "INSERT INTO handle(handle, noid, modify_date) VALUES(?,?,?)"

        sql, outputData = createInsertSQL(testHandle, testNoid)

        self.assertEqual(sql, expectedSQL)
        self.assertEqual(outputData[:2], (testHandle, testNoid))

    def test_createUpdateSQL(self):

        testHandle = "1910/2020"
        expectedSQL = "UPDATE handle SET modify_date = ? WHERE handle = ?"

        sql, outputData = createUpdateSQL(testHandle)

        self.assertEqual(sql, expectedSQL)
        self.assertEqual(outputData[1:], (testHandle,))

    def test_getRecordsWithValues(self):

        rec1, rec2 = ["1", "title1"], ["2", "title2"]
        testOAIRecords = [rec1, rec2]

        outputRecords = getRecordsWithValues(testOAIRecords)
        self.assertEqual(outputRecords, ["title1", "title2"])

        rec1, rec2 = ["1", "title1"], ["2"]
        testOAIRecords = [rec1, rec2]

        outputRecords = getRecordsWithValues(testOAIRecords)
        self.assertEqual(outputRecords, ["title1"])

        testOAIRecords = []
        outputRecords = getRecordsWithValues(testOAIRecords)
        self.assertEqual(outputRecords, [])

    def test_createTarFile(self):

        # Prepare files in the source folder
        testFile1 = "test1.txt"
        testFile2 = "test2.txt"
        content = "content2"
        tempPath = tempfile.TemporaryDirectory().name
        sourceFolder = tempfile.mkdtemp()
        sourceFolderPath = sourceFolder + "/"

        saveToTargetFile(testFile1, content, sourceFolderPath)
        saveToTargetFile(testFile2, content, sourceFolderPath)

        # Create a test tar file in the target folder
        targetFolder = tempfile.mkdtemp()
        targetFolderPath = targetFolder + "/"
        fileName = "test.tar"
        createTarFile(fileName, sourceFolderPath, targetFolderPath)

        self.assertTrue(tarfile.is_tarfile(targetFolderPath + fileName))

        # Untar tarfile
        validateFolder = tempfile.mkdtemp()
        validateFolderPath = targetFolder + "/"
        tarTempFile = tarfile.open(targetFolderPath + fileName)
        tarTempFile.extractall(validateFolderPath)
        targetFolderFiles = os.listdir(validateFolderPath)
        expected = ['test.tar', 'test1.txt', 'test2.txt']

        self.assertListEqual(targetFolderFiles, expected)

    def test_saveToTargetFile(self):

        fileName = "test.txt"
        content = "content"

        with tempfile.TemporaryDirectory() as tmpdirname:
            tempPath = tmpdirname
            saveToTargetFile(fileName, content, tempPath)

            f = open(tmpdirname + fileName, "r")
            self.assertEqual(f.read(), "content")

    def test_createBagit(self):

        # Prepare files in the source folder
        testFile1 = "test1.txt"
        testFile2 = "test2.txt"
        content = "content2"
        tempPath = tempfile.TemporaryDirectory().name
        sourceFolder = tempfile.mkdtemp()
        sourceFolderPath = sourceFolder + "/"

        saveToTargetFile(testFile1, content, sourceFolderPath)
        saveToTargetFile(testFile2, content, sourceFolderPath)

        testConfigData = {
            'aptrust': {
                'organization': 'VT',
                'group_id': '12345',
                'desc': 'Desc'}}
        testNoid = "zxcvb"
        testfileCount = [1, 1]

        bagitInfo = createBagitInfo(testConfigData, testNoid, testfileCount)
        checksum = ["md5", "sha256"]

        createBagit(sourceFolderPath, bagitInfo, checksum)

        sourceFolderFiles = os.listdir(sourceFolderPath)
        expected = [
            'tagmanifest-md5.txt',
            'bagit.txt',
            'bag-info.txt',
            'tagmanifest-sha256.txt',
            'manifest-md5.txt',
            'data',
            'manifest-sha256.txt']
        self.assertListEqual(sourceFolderFiles, expected)

        sourceFolderDataFiles = os.listdir(sourceFolderPath + "data/")
        expected = ['test1.txt', 'test2.txt']
        self.assertListEqual(sourceFolderDataFiles, expected)
