from unittest import TestCase
from dspace_aip_archiver import * 

class TestSuite(TestCase):

    def test_get_handle(self):
        
        record = ['AR200304.pdf', 'http://hdl.handle.net/10919/8147']
        output = get_handle(record)
        expected = "10919/8147"
        self.assertEqual(output, expected)