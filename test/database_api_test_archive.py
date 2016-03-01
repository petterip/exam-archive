'''
Testing class for database API's archive related functions.

Authors: Ari Kairala, Petteri Ponsimaa
Originally adopted from Ivan's exercise 1 test class.
'''

import sqlite3, unittest, pytest

from database_api_test_common import BaseTestCase, db, db_path
from exam_archive import ExamDatabaseErrorNotFound, ExamDatabaseErrorExists

class ArchiveTestCase(BaseTestCase):
    '''
    ArchiveTestCase contains archive related unit tests of the database API.
    '''

    # Define a list of the sample contents of the database, so we can later compare it to the test results
    expected_archive = [{'archive_id': 1, 'archive_name': 'Information Processing Science', 'identification_needed': 1,
                         'last_modified': '2015-02-26', 'organisation_name': 'Blanko', 'modifier_id': 1},

                        {'archive_id': 2, 'archive_name': 'Wireless Communications Engineering',
                         'identification_needed': 1, 'last_modified': '2015-03-03', 'organisation_name': 'OTiT',
                         'modifier_id': 1},

                        {'archive_id': 3, 'archive_name': 'Electrical Engineering', 'identification_needed': 1,
                         'last_modified': '2015-03-03', 'organisation_name': 'SIK', 'modifier_id': 1}]

    archive_initial_size = 3

    @classmethod
    def setUpClass(cls):
        print "Testing ", cls.__name__

    def test_archive_table_created(self):
        '''
        Checks that the archive table initially contains the expected rows from exam_archive_data_dump.sql so we
        are ready to run the following unit tests.
        '''
        print '(' + self.test_archive_table_created.__name__ + ')', \
            self.test_archive_table_created.__doc__

        #Create the SQL Statement
        keys_on = 'PRAGMA foreign_keys = ON'
        query1 = 'SELECT * FROM archive'

        #Connects to the database.
        con = sqlite3.connect(db_path)
        with con:
            #Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            #Provide support for foreign keys
            cur.execute(keys_on)
            #Execute main SQL Statement
            cur.execute(query1)
            users = cur.fetchall()
            # Assert that we do what was expected (3 rows)
            self.assertEquals(len(users), len(self.expected_archive))

        if con:
            con.close()

    def test_create_object(self):
        '''
        Check that the method _create_object works by returning the correct values
        for the first database row.
        '''
        print '(' + self.test_create_object.__name__ + ')', \
            self.test_create_object.__doc__

        #Create the SQL Statement
        keys_on = 'PRAGMA foreign_keys = ON'
        query = 'SELECT * FROM archive WHERE archive_id = 1'

        #Connects to the database.
        con = sqlite3.connect(db_path)
        with con:
            #Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            #Provide support for foreign keys
            cur.execute(keys_on)
            #Execute main SQL Statement
            cur.execute(query)
            #Extrac the row
            row = cur.fetchone()
            #Test the method
            archive = db._create_object(row)
            self.assertDictContainsSubset(archive, self.expected_archive[0])

    def test_create_archive(self):
        '''
        Test that a new archive can be created
        '''
        print '(' + self.test_create_archive.__name__ + ')', \
            self.test_create_archive.__doc__
        archive_id = db.create_archive("TestArchive", "TestOrg", True, 1)
        self.assertIsNotNone(archive_id)

        #Get the expected modified message
        new_archive = {'archive_id': archive_id,
                       'archive_name': "TestArchive",
                       'organisation_name': "TestOrg",
                       'identification_needed': True,
                       'modifier_id': 1}

        #Create the SQL Statement
        keys_on = 'PRAGMA foreign_keys = ON'
        query = 'SELECT * FROM archive WHERE archive_id = ?'

        # Connects to the database.
        con = sqlite3.connect(db_path)
        with con:
            #Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            #Provide support for foreign keys
            cur.execute(keys_on)
            #Execute main SQL Statement
            cur.execute(query, (archive_id,))
            #Extrac the row
            row = cur.fetchone()
            # Let's check that there was at least one matching row
            self.assertIsNotNone(row)
            #Test the method
            archive = db._create_object(row)
            self.assertDictContainsSubset(new_archive, archive)

        # Check that a row can not be added twice: "Archive already has an entry ..."
        self.assertRaises(ExamDatabaseErrorExists, db.create_archive, "TestArchive", "TestOrg", False, 1)

        # Check for foreign key constraints: "Modifier does not exist"
        self.assertRaises(ExamDatabaseErrorNotFound, db.create_archive, "TestArchive", "TestOrg", False, 999)

    def test_remove_archive(self):
        '''
        Test that an archive can be deleted
        '''
        print '(' + self.test_remove_archive.__name__ + ')', \
            self.test_remove_archive.__doc__

        archive_id = db.create_archive("TestArchiveDelete", "TestOrg", True, 1)

        # Delete the archive we created
        ret = db.remove_archive(archive_id)
        self.assertEquals(ret, True)

        # Try to delete again the archive we created, should fail
        ret = db.remove_archive(archive_id)
        self.assertEquals(ret, False)

    def test_get_archive(self):
        '''
        Test get_archive with id 1
        '''
        archive_id = 2
        print '(' + self.test_get_archive.__name__ + ')', \
            self.test_get_archive.__doc__

        # Test an existing archive
        archive = db.get_archive(archive_id)
        self.assertDictContainsSubset(archive, self.expected_archive[1])

    def test_get_archive_nonexisting(self):
        '''
        Test get_archive with non-existing id of 999 and non-existing name of 'XYZ'
        '''
        no_archive_id = 999
        no_archive_name = 'XYZ'

        print '(' + self.test_get_archive_nonexisting.__name__ + ')', \
            self.test_get_archive_nonexisting.__doc__

        # Test with an non-existing archive
        message = db.get_archive(no_archive_id)
        self.assertIsNone(message)

        # Test with an non-existing archive
        message = db.get_archive_by_name(no_archive_name)
        self.assertIsNone(message)

    def test_get_archive_by_name(self):
        '''
        Test get_archive_by_name with name 'Blanko'
        '''
        archive_name = 'Information Processing Science'
        print '(' + self.test_get_archive.__name__ + ')', \
            self.test_get_archive.__doc__

        # Test an existing archive
        archive = db.get_archive_by_name(archive_name)
        self.assertDictContainsSubset(archive, self.expected_archive[0])

    def test_browse_archives(self):
        '''
        Test that browse_archives works correctly by fetching 3 archives, only one and non-existing archives
        '''
        # (self, limit=-1, offset=0, offset_represents_ids=False):

        print '(' + self.test_browse_archives.__name__ + ')', self.test_browse_archives.__doc__

        # Try browsing the archive with parameter combinations testing the limits. First, check that we get the same
        # correct number of archives with the contents in expected_archive list.
        archives = db.browse_archives()
        self.assertEquals(len(archives), 3)
        self.assertListEqual(archives, self.expected_archive)

        # The same as above but with default parameters
        archives = db.browse_archives(limit=-1, offset=0)
        self.assertEquals(len(archives), 3)
        self.assertListEqual(archives, self.expected_archive)

        # Get only the second row, using offset as the ID of the archive (essentially same as get_archive(1) )
        archives = db.browse_archives(limit=1, offset=1, offset_represents_ids=True)
        self.assertEquals(len(archives), 1)
        self.assertDictEqual(archives[0], self.expected_archive[0])

        # Try the get archives that are not there
        archives = db.browse_archives(1000, 100, False)
        self.assertEquals(len(archives), 0)
        self.assertListEqual(archives, [])

if __name__ == '__main__':
    print 'Start running tests'
    unittest.main()
