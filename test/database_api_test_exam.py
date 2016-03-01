'''
Testing class for database API's exam related functions.

Authors: Ari Kairala, Petteri Ponsimaa
Originally adopted from Ivan's exercise 1 test class.
'''

import sqlite3, unittest, pytest

from database_api_test_common import BaseTestCase, db, db_path
from exam_archive import ExamDatabaseErrorNotFound, ExamDatabaseErrorExists


class ExamTestCase(BaseTestCase):
    '''
    ExamTestCase contains exam related unit tests of the database API.
    '''

    # Define a list of the sample contents of the database, so we can later compare it to the test results
    expected_exam = [
        {'examiner_id': 2, 'language_id': 'fi', 'date': '2013-02-21', 'last_modified': '2015-02-26', 'exam_id': 1,
         'course_id': 1, 'file_attachment': '810136P_exam01.pdf', 'modifier_id': '1'},
        {'examiner_id': 2, 'language_id': 'fi', 'date': '2014-02-28', 'last_modified': '2015-02-26', 'exam_id': 2,
         'course_id': 1, 'file_attachment': '810136P_exam02.pdf', 'modifier_id': '1'},
        {'examiner_id': 2, 'language_id': 'fi', 'date': '2015-05-05', 'last_modified': '2015-03-03', 'exam_id': 3,
         'course_id': 1, 'file_attachment': '810136P_exam03.pdf', 'modifier_id': '1'}]

    exam_initial_size = 3

    @classmethod
    def setUpClass(cls):
        print "Testing ", cls.__name__

    def test_exam_table_created(self):
        '''
        Checks that the exam table initially contains the expected rows from exam_archive_data_dump.sql so we
        are ready to run the following unit tests.
        '''
        print '(' + self.test_exam_table_created.__name__ + ')', \
            self.test_exam_table_created.__doc__

        # Create the SQL Statement
        keys_on = 'PRAGMA foreign_keys = ON'
        query1 = 'SELECT * FROM exam WHERE course_id = 1'

        # Connects to the database.
        con = sqlite3.connect(db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)
            # Execute main SQL Statement
            cur.execute(query1)
            users = cur.fetchall()
            # Assert that we do what was expected (3 rows)
            self.assertEquals(len(users), len(self.expected_exam))

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
        query = 'SELECT * FROM exam WHERE exam_id = 1'

        # Connects to the database.
        con = sqlite3.connect(db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)
            # Execute main SQL Statement
            cur.execute(query)
            # Extrac the row
            row = cur.fetchone()
            #Test the method
            exam = db._create_object(row)
            self.assertDictContainsSubset(exam, self.expected_exam[0])

    def test_create_exam(self):
        '''
        Test that a new exam can be created
        '''
        print '(' + self.test_create_exam.__name__ + ')', \
            self.test_create_exam.__doc__

        exam_id = db.create_exam(1, 1, "2015-03-04", "abc.pdf", "fi", 1)
        self.assertIsNotNone(exam_id)

        # Set the expected exam
        new_exam = {'examiner_id': 1, 'language_id': 'fi', 'date': '2015-03-04', 'exam_id': exam_id,
                    'course_id': 1, 'file_attachment': 'abc.pdf', 'modifier_id': '1'}

        # Create the SQL Statement
        keys_on = 'PRAGMA foreign_keys = ON'
        query = 'SELECT * FROM exam WHERE exam_id = ?'

        # Connects to the database.
        con = sqlite3.connect(db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)
            # Execute main SQL Statement
            cur.execute(query, (exam_id,))
            # Extrac the row
            row = cur.fetchone()
            # Let's check that there was at least one matching row
            self.assertIsNotNone(row)
            #Test the method
            exam = db._create_object(row)
            self.assertDictContainsSubset(new_exam, exam)

        # Check that a row can not be added twice: "Exam already exists within the same course and date"
        self.assertRaises(ExamDatabaseErrorExists, db.create_exam, 1, 2, "2015-03-04", "abc.pdf", "fi", 1)

        # Check for foreign key constraints: "Course does not exist"
        self.assertRaises(ExamDatabaseErrorNotFound, db.create_exam, 999, 1, "2015-11-11", "abc.pdf", "fi", 1)

        # Check for foreign key constraints: "Language does not exist"
        self.assertRaises(ExamDatabaseErrorNotFound, db.create_exam, 1, 1, "2015-11-11", "abc.pdf", "XX", 1)

        # Check for foreign key constraints: "Examiner does not exist"
        self.assertRaises(ExamDatabaseErrorNotFound, db.create_exam, 1, 999, "2015-11-11", "abc.pdf", "fi", 1)

        # Check for foreign key constraints: "Modifier does not exist"
        self.assertRaises(ExamDatabaseErrorNotFound, db.create_exam, 1, 1, "2015-11-11", "abc.pdf", "fi", 999)

    def test_edit_exam(self):
        '''
        Test that a exam can be modified
        '''
        print '(' + self.test_create_exam.__name__ + ')', \
            self.test_create_exam.__doc__

        exam_id = db.create_exam(1, 1, "2015-03-04", "abc.pdf", "fi", 1)
        self.assertIsNotNone(exam_id)

        ret = db.edit_exam(exam_id=exam_id, course_id=2, examiner_id=None, date="2015-05-06",
                           file_attachment="def.pdf", language_id="en", modifier_id=2)
        self.assertIsNotNone(ret)

        # Set the expected exam
        new_exam = {'examiner_id': None, 'language_id': 'en', 'date': '2015-05-06', 'exam_id': exam_id,
                    'course_id': 2, 'file_attachment': 'def.pdf', 'modifier_id': '2'}

        # Create the SQL Statement
        keys_on = 'PRAGMA foreign_keys = ON'
        query = 'SELECT * FROM exam WHERE exam_id = ?'

        # Connects to the database.
        con = sqlite3.connect(db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)
            # Execute main SQL Statement
            cur.execute(query, (exam_id,))
            # Extrac the row
            row = cur.fetchone()
            # Let's check that there was at least one matching row
            self.assertIsNotNone(row)
            #Test the method
            exam = db._create_object(row)
            self.assertDictContainsSubset(new_exam, exam)

        # Create second exam for testing a conflict rising from trying to have two exams with the same course and date
        second_exam_id = db.create_exam(1, 1, "2015-03-04", "abc.pdf", "fi", 1)
        self.assertIsNotNone(second_exam_id)

        # Check that a row can not be added twice: "Exam already exists within the same course and date"
        self.assertRaises(ExamDatabaseErrorExists, db.edit_exam, exam_id, 1, 2, "2015-03-04", "abc.pdf", "fi", 1)

        # Check for foreign key constraints: "Course does not exist"
        self.assertRaises(ExamDatabaseErrorNotFound, db.edit_exam, exam_id, 999, 1, "2015-11-11", "abc.pdf", "fi", 1)

        # Check for foreign key constraints: "Language does not exist"
        self.assertRaises(ExamDatabaseErrorNotFound, db.edit_exam, exam_id, 1, 1, "2015-11-11", "abc.pdf", "XX", 1)

        # Check for foreign key constraints: "Examiner does not exist"
        self.assertRaises(ExamDatabaseErrorNotFound, db.edit_exam, exam_id, 1, 999, "2015-11-11", "abc.pdf", "fi", 1)

        # Check for foreign key constraints: "Modifier does not exist"
        self.assertRaises(ExamDatabaseErrorNotFound, db.edit_exam, exam_id, 1, 1, "2015-11-11", "abc.pdf", "fi", 999)


    def test_edit_exam_file(self):
        '''
        Test that the file attachmend of exam can be modified
        '''
        print '(' + self.test_create_exam.__name__ + ')', \
            self.test_create_exam.__doc__

        exam_id = db.create_exam(1, 1, "2015-03-04", "abc.pdf", "en", 1)
        self.assertIsNotNone(exam_id)

        ret = db.edit_exam_file(exam_id=exam_id, file_attachment="def.pdf", modifier_id=2)
        self.assertIsNotNone(ret)

        # Set the expected exam
        new_exam = {'examiner_id': 1, 'language_id': 'en', 'date': '2015-03-04', 'exam_id': exam_id,
                    'course_id': 1, 'file_attachment': 'def.pdf', 'modifier_id': '2'}

        # Create the SQL Statement
        keys_on = 'PRAGMA foreign_keys = ON'
        query = 'SELECT * FROM exam WHERE exam_id = ?'

        # Connects to the database.
        con = sqlite3.connect(db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)
            # Execute main SQL Statement
            cur.execute(query, (exam_id,))
            # Extrac the row
            row = cur.fetchone()
            # Let's check that there was at least one matching row
            self.assertIsNotNone(row)
            #Test the method
            exam = db._create_object(row)
            self.assertDictContainsSubset(new_exam, exam)

        # Check for foreign key constraints: "Modifier does not exist"
        self.assertRaises(ExamDatabaseErrorNotFound, db.edit_exam_file, exam_id, "abc.pdf", 999)


    def test_remove_exam(self):
        '''
        Test that an exam can be deleted
        '''
        print '(' + self.test_remove_exam.__name__ + ')', \
            self.test_remove_exam.__doc__

        exam_id = db.create_exam(1, 1, "2015-02-04", "abc.pdf", "en", 1)

        # Delete the exam we created
        ret = db.remove_exam(exam_id)
        self.assertEquals(ret, True)

        # Try to delete again the exam we created, should fail
        ret = db.remove_exam(exam_id)
        self.assertEquals(ret, False)

    def test_get_exam(self):
        '''
        Test get_exam with id 1
        '''
        exam_id = 2
        print '(' + self.test_get_exam.__name__ + ')', \
            self.test_get_exam.__doc__

        # Test an existing exam
        exam = db.get_exam(exam_id)
        self.assertDictContainsSubset(exam, self.expected_exam[1])

    def test_get_exam_nonexisting_id(self):
        '''
        Test get_exam with non-existing id of 999
        '''
        no_exam_id = 999
        print '(' + self.test_get_exam_nonexisting_id.__name__ + ')', \
            self.test_get_exam_nonexisting_id.__doc__
        # Test with an non-existing exam
        message = db.get_exam(no_exam_id)
        self.assertIsNone(message)

    def test_browse_exams(self):
        '''
        Test that browse_exams works correctly by fetching 3 exams, only one and non-existing exams
        '''
        # (self, limit=-1, offset=0, offset_represents_ids=False):

        print '(' + self.test_browse_exams.__name__ + ')', self.test_browse_exams.__doc__

        # Try browsing one archive's exams with parameter combinations testing the limits. First, check that we
        # get the same correct number of exams with the contents in expected_exam list.
        exams = db.browse_exams(1)
        self.assertEquals(len(exams), 3)
        self.assertListEqual(exams, self.expected_exam)

        # The same as above but with default parameters
        exams = db.browse_exams(1, limit=-1, offset=0)
        self.assertEquals(len(exams), 3)
        self.assertListEqual(exams, self.expected_exam)

        # Get only the second row, using offset as the ID of the exam (essentially same as get_exam(1) )
        exams = db.browse_exams(1, limit=1, offset=1, offset_represents_ids=True)
        self.assertEquals(len(exams), 1)
        self.assertDictEqual(exams[0], self.expected_exam[0])

        # Try the get exams that are not there
        exams = db.browse_exams(1, 1000, 100, False)
        self.assertEquals(len(exams), 0)
        self.assertListEqual(exams, [])


if __name__ == '__main__':
    print 'Start running tests'
    unittest.main()
