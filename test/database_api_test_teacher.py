'''
Testing class for database API's teacher related functions.

Authors: Ari Kairala, Petteri Ponsimaa
Originally adopted from Ivan's exercise 1 test class.
'''

import sqlite3, unittest, pytest

from database_api_test_common import BaseTestCase, db, db_path
from exam_archive import ExamDatabaseErrorNotFound, ExamDatabaseErrorExists


class TeacherTestCase(BaseTestCase):
    '''
    TeacherTestCase contains teacher related unit tests of the database API.
    '''

    # Define a list of the sample contents of the database, so we can later compare it to the test results
    expected_teachers = [
        {'teacher_id': 1, 'city': u'OULU', 'first_name': u'Tero', 'last_name': u'Testaaja', 'office': u'TOL301',
         'other_info': None, 'phone': u'+358401231231', 'last_modified': u'2015-02-26', 'postal_code': u'90500',
         'modifier_id': u'1', 'email': u'tero.testaaja@oulu.fi', 'street_address': u'Testiosoite 123'},

        {'teacher_id': 2, 'city': u'OULU', 'first_name': u'Terhi', 'last_name': u'Testi', 'office': u'TOL301',
         'other_info': None, 'phone': u'+358404564566', 'last_modified': u'2015-02-26', 'postal_code': u'90500',
         'modifier_id': u'1', 'email': u'terhi.testi@oulu.fi', 'street_address': u'Testikuja 12 A 1'}]

    teacher_initial_size = 2

    @classmethod
    def setUpClass(cls):
        print "Testing ", cls.__name__

    def test_teacher_table_created(self):
        '''
        Checks that the teacher table initially contains the expected rows from exam_teacher_data_dump.sql so we
        are ready to run the following unit tests.
        '''
        print '(' + self.test_teacher_table_created.__name__ + ')', \
            self.test_teacher_table_created.__doc__

        # Create the SQL Statement
        keys_on = 'PRAGMA foreign_keys = ON'
        query1 = 'SELECT * FROM teacher'

        # Connects to the database.
        con = sqlite3.connect(db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            #Provide support for foreign keys
            cur.execute(keys_on)
            #Execute main SQL Statement
            cur.execute(query1)
            users = cur.fetchall()
            # Assert that we do what was expected (3 rows)
            self.assertEquals(len(users), len(self.expected_teachers))

        if con:
            con.close()

    def test_create_object(self):
        '''
        Check that the method _create_object works by returning the correct values
        for the first database row.
        '''
        print '(' + self.test_create_object.__name__ + ')', \
            self.test_create_object.__doc__

        # Create the SQL Statement
        keys_on = 'PRAGMA foreign_keys = ON'
        query = 'SELECT * FROM teacher WHERE teacher_id = 1'

        # Connects to the database.
        con = sqlite3.connect(db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            #Provide support for foreign keys
            cur.execute(keys_on)
            #Execute main SQL Statement
            cur.execute(query)
            #Extrac the row
            row = cur.fetchone()
            #Test the method
            teacher = db._create_object(row)
            self.assertDictContainsSubset(teacher, self.expected_teachers[0])

    def test_create_teacher(self):
        '''
        Test that a new teacher can be created
        '''
        print '(' + self.test_create_teacher.__name__ + ')', \
            self.test_create_teacher.__doc__
        teacher_id = db.create_teacher('Liisa', 'Tomera', office='GF301', street_address='Testiosoite 123',
                                       postal_code='90580', city='Oulu', phone='+358401231231',
                                       email='liisa.tomera@oulu.fi', other_info=None, modifier_id='1')
        self.assertIsNotNone(teacher_id)

        # Get the expected modified message
        new_teacher = {'teacher_id': teacher_id, 'city': 'Oulu', 'first_name': 'Liisa', 'last_name': 'Tomera',
                       'office': 'GF301', 'other_info': None, 'phone': '+358401231231', 'postal_code': '90580',
                       'modifier_id': '1', 'email': 'liisa.tomera@oulu.fi', 'street_address': 'Testiosoite 123'}

        # Create the SQL Statement
        keys_on = 'PRAGMA foreign_keys = ON'
        query = 'SELECT * FROM teacher WHERE teacher_id = ?'

        # Connects to the database.
        con = sqlite3.connect(db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            #Provide support for foreign keys
            cur.execute(keys_on)
            #Execute main SQL Statement
            cur.execute(query, (teacher_id,))
            #Extrac the row
            row = cur.fetchone()
            # Let's check that there was at least one matching row
            self.assertIsNotNone(row)
            #Test the method
            teacher = db._create_object(row)
            self.assertDictContainsSubset(new_teacher, teacher)

        # Check for value error: "Teacher's email address is malformed"
        self.assertRaises(ValueError, db.create_teacher, 'Liisa', 'Tomera', office='GF301',
                          street_address='Kotikonttori 1',
                          postal_code='90580', city='Oulu', phone='+358401231231',
                          email='malformed.email.address', other_info='', modifier_id=None)

        # Check for value error: "First and last name must be given"
        self.assertRaises(ValueError, db.create_teacher, '', 'Tomera', office='GF301',
                          street_address='Kotikonttori 1',
                          postal_code='90580', city='Oulu', phone='+358401231231',
                          email='tero.tomera@oulu.fi', other_info='', modifier_id=None)

        # Check for foreign key constraints: "Modifier does not exist"
        self.assertRaises(ExamDatabaseErrorExists, db.create_teacher, 'Tero', 'Tomera', office='GF301',
                          street_address='Kotikonttori 2',
                          postal_code='90580', city='Oulu', phone='+358401231233',
                          email='tero.tomera@oulu.fi', other_info='', modifier_id=999)

    def test_remove_teacher(self):
        '''
        Test that an teacher can be deleted
        '''
        print '(' + self.test_remove_teacher.__name__ + ')', \
            self.test_remove_teacher.__doc__

        teacher_id = db.create_teacher('Keijo', 'Tomera')

        # Delete the teacher we created
        ret = db.remove_teacher(teacher_id)
        self.assertEquals(ret, True)

        # Try to delete again the teacher we created, should fail
        ret = db.remove_teacher(teacher_id)
        self.assertEquals(ret, False)

    def test_get_teacher(self):
        '''
        Test get_teacher with id 1
        '''
        teacher_id = 2
        print '(' + self.test_get_teacher.__name__ + ')', \
            self.test_get_teacher.__doc__

        # Test an existing teacher
        teacher = db.get_teacher(teacher_id)
        self.assertDictContainsSubset(teacher, self.expected_teachers[1])

    def test_get_teacher_nonexisting(self):
        '''
        Test get_teacher with non-existing id of 999 and non-existing name of 'XYZ'
        '''
        no_teacher_id = 999
        no_teacher_name = 'XYZ'

        print '(' + self.test_get_teacher_nonexisting.__name__ + ')', \
            self.test_get_teacher_nonexisting.__doc__

        # Test with an non-existing teacher
        message = db.get_teacher(no_teacher_id)
        self.assertIsNone(message)

        # Test with an non-existing teacher
        message = db.get_teacher_by_name('Liisa', 'Testaaja')
        self.assertIsNone(message)

        # Test with an non-existing teacher
        message = db.get_teacher_by_name('Liisa', None)
        self.assertIsNone(message)

    def test_get_teacher_by_name(self):
        '''
        Test get_teacher_by_name with name 'Tero Testaaja'
        '''
        print '(' + self.test_get_teacher.__name__ + ')', \
            self.test_get_teacher.__doc__

        # Test an existing teacher
        teacher = db.get_teacher_by_name('Tero', 'Testaaja')
        self.assertDictContainsSubset(teacher, self.expected_teachers[0])

    def test_browse_teachers(self):
        '''
        Test that browse_teachers works correctly by fetching 3 teachers, only one and non-existing teachers
        '''
        # (self, limit=-1, offset=0, offset_represents_ids=False):

        print '(' + self.test_browse_teachers.__name__ + ')', self.test_browse_teachers.__doc__

        # Try browsing the teacher with parameter combinations testing the limits. First, check that we get the same
        # correct number of teachers with the contents in expected_teachers list.
        teachers = db.browse_teachers()
        self.assertEquals(len(teachers), len(self.expected_teachers))
        self.assertListEqual(teachers, self.expected_teachers)

        # The same as above but with default parameters
        teachers = db.browse_teachers(limit=-1, offset=0)
        self.assertEquals(len(teachers), len(self.expected_teachers))
        self.assertListEqual(teachers, self.expected_teachers)

        # Get only the second row, using offset as the ID of the teacher (essentially same as get_teacher(1) )
        teachers = db.browse_teachers(limit=1, offset=1, offset_represents_ids=True)
        self.assertEquals(len(teachers), 1)
        self.assertDictEqual(teachers[0], self.expected_teachers[0])

        # Try the get teachers that are not there
        teachers = db.browse_teachers(1000, 100, False)
        self.assertEquals(len(teachers), 0)
        self.assertListEqual(teachers, [])


if __name__ == '__main__':
    print 'Start running tests'
    unittest.main()
