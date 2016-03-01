'''
Testing class for database API's course related functions.

Authors: Ari Kairala, Petteri Ponsimaa
Originally adopted from Ivan's exercise 1 test class.
'''

import sqlite3, unittest, pytest

from database_api_test_common import BaseTestCase, db, db_path
from exam_archive import ExamDatabaseErrorNotFound, ExamDatabaseErrorExists


class CourseTestCase(BaseTestCase):
    '''
    CourseTestCase contains course related unit tests of the database API.
    '''

    # Define a list of the sample contents of the database, so we can later compare it to the test results
    expected_course = [{'archive_id': 1, 'teacher_id': 1, 'course_name': u'Johdatus tietojenk\xe4sittelytieteisiin',
                        'description': 'Lorem ipsum', 'url': 'http://weboodi.oulu.fi/', 'language_id': 'fi',
                        'credit_points': 4, 'last_modified': '2015-02-26', 'course_id': 1, 'course_code': '810136P',
                        'modifier_id': '1'},

                       {'archive_id': 1, 'teacher_id': 1, 'course_name': 'Usability Testing',
                        'description': 'Lorem ipsum', 'url': 'http://weboodi.oulu.fi/', 'language_id': 'en',
                        'credit_points': 5, 'last_modified': '2015-02-26', 'course_id': 2, 'course_code': '812671S',
                        'modifier_id': '1'},

                       {'archive_id': 1, 'teacher_id': 1,
                        'course_name': 'Software Engineering Management Measurement and Improvement',
                        'description': 'Lorem ipsum', 'url': 'http://weboodi.oulu.fi/',
                        'language_id': 'en', 'credit_points': 5, 'last_modified': '2015-03-03',
                        'course_id': 3, 'course_code': '815660S', 'modifier_id': '1'}]

    course_initial_size = 3

    @classmethod
    def setUpClass(cls):
        print "Testing ", cls.__name__

    def test_course_table_created(self):
        '''
        Checks that the course table initially contains the expected rows from exam_archive_data_dump.sql so we
        are ready to run the following unit tests.
        '''
        print '(' + self.test_course_table_created.__name__ + ')', \
            self.test_course_table_created.__doc__

        # Create the SQL Statement
        keys_on = 'PRAGMA foreign_keys = ON'
        query1 = 'SELECT * FROM course'

        # Connects to the database.
        con = sqlite3.connect(db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)
            #Execute main SQL Statement
            cur.execute(query1)
            users = cur.fetchall()
            #Assert that we do what was expected (3 rows)
            self.assertEquals(len(users), len(self.expected_course))

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
        query = 'SELECT * FROM course WHERE course_id = 1'

        # Connects to the database.
        con = sqlite3.connect(db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)
            #Execute main SQL Statement
            cur.execute(query)
            #Extrac the row
            row = cur.fetchone()
            #Test the method
            course = db._create_object(row)
            self.assertDictContainsSubset(course, self.expected_course[0])

    def test_create_course(self):
        '''
        Test that a new course can be created
        '''
        print '(' + self.test_create_course.__name__ + ')', \
            self.test_create_course.__doc__

        course_id = db.create_course(1, "123456A", "TestCourse", "Test description", 1, 'http://example.com', 5, "fi")
        self.assertIsNotNone(course_id)

        # Get the expected modified message
        new_course = {'course_id': course_id,
                      'archive_id': 1, 'course_code': "123456A",
                      'course_name': "TestCourse",
                      'description': "Test description",
                      'teacher_id': 1, 'url': 'http://example.com',
                      'credit_points': 5, 'language_id': 'fi',
                      'modifier_id': None}

        # Create the SQL Statement
        keys_on = 'PRAGMA foreign_keys = ON'
        query = 'SELECT * FROM course WHERE course_id = ?'

        # Connects to the database.
        con = sqlite3.connect(db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)
            #Execute main SQL Statement
            cur.execute(query, (course_id,))
            #Extrac the row
            row = cur.fetchone()
            # Let's check that there was at least one matching row
            self.assertIsNotNone(row)
            #Test the method
            course = db._create_object(row)
            self.assertDictContainsSubset(new_course, course)

        # Check that a row can not be added twice: "Course already exists with the same name and language"
        self.assertRaises(ExamDatabaseErrorExists, db.create_course, 1, "DIFFERENT", "TestCourse", "Different", 2,
                          'http://abc.com', 2, "fi")

        # Check for foreign key constraints: "Archive does not exist"
        self.assertRaises(ExamDatabaseErrorNotFound, db.create_course, 999, "123456A", "TestCourse", "Test description",
                          1, 'http://example.com', 5, "fi")

        # Check for foreign key constraints: "Language does not exist"
        self.assertRaises(ExamDatabaseErrorNotFound, db.create_course, 1, "123456A", "TestCourse", "Test description", 1,
                          'http://example.com', 5, "XX")

        # Check for foreign key constraints: "Teacher does not exist"
        self.assertRaises(ExamDatabaseErrorNotFound, db.create_course, 1, "123456A", "TestCourse", "Test description",
                          999, 'http://example.com', 5, "fi")

        # Check for foreign key constraints: "Modifier does not exist"
        self.assertRaises(ExamDatabaseErrorNotFound, db.create_course, 1, "456789A", "TestCourse2", "Test description", 1,
                          'http://example.com', 5, "fi", 999)

    def test_remove_course(self):
        '''
        Test that an course can be deleted
        '''
        print '(' + self.test_remove_course.__name__ + ')', \
            self.test_remove_course.__doc__

        course_id = db.create_course(2, "123456A", "DeleteCourse", "Test description", 1, 'http://example.com', 5, "fi")

        # Delete the course we created
        ret = db.remove_course(course_id)
        self.assertEquals(ret, True)

        # Try to delete again the course we created, should fail
        ret = db.remove_course(course_id)
        self.assertEquals(ret, False)

    def test_get_course(self):
        '''
        Test get_course with id 1
        '''
        course_id = 2
        print '(' + self.test_get_course.__name__ + ')', \
            self.test_get_course.__doc__

        # Test an existing course
        course = db.get_course(course_id)
        self.assertDictContainsSubset(course, self.expected_course[1])

    def test_get_course_nonexisting(self):
        '''
        Test get_course with non-existing id of 999 and non-existing name of 'XYZ'
        '''
        no_course_id = 999
        no_course_name = 'XYZ'

        print '(' + self.test_get_course_nonexisting.__name__ + ')', \
            self.test_get_course_nonexisting.__doc__

        # Test with an non-existing course
        course = db.get_course(no_course_id)
        self.assertIsNone(course)

        # Test with an non-existing course
        course = db.get_course_by_name(no_course_name)
        self.assertIsNone(course)

    def test_get_course_by_name(self):
        '''
        Test get_course_by_name with name 'Blanko'
        '''
        course_name = 'Usability Testing'
        print '(' + self.test_get_course_by_name.__name__ + ')', \
            self.test_get_course_by_name.__doc__

        # Test an existing course
        course = db.get_course_by_name(course_name)
        self.assertDictContainsSubset(course, self.expected_course[1])

    def test_browse_courses(self):
        '''
        Test that browse_courses works correctly by fetching 3 courses, only one and non-existing courses
        '''
        # (self, limit=-1, offset=0, offset_represents_ids=False):

        print '(' + self.test_browse_courses.__name__ + ')', self.test_browse_courses.__doc__

        # Try browsing one archive's courses with parameter combinations testing the limits. First, check that we
        # get the same correct number of courses with the contents in expected_course list.
        courses = db.browse_courses(1)
        self.assertEquals(len(courses), 3)
        self.assertListEqual(courses, self.expected_course)

        # The same as above but with default parameters
        courses = db.browse_courses(1, limit=-1, offset=0)
        self.assertEquals(len(courses), 3)
        self.assertListEqual(courses, self.expected_course)

        # Get only the second row, using offset as the ID of the course (essentially same as get_course(1) )
        courses = db.browse_courses(1, limit=1, offset=1, offset_represents_ids=True)
        self.assertEquals(len(courses), 1)
        self.assertDictEqual(courses[0], self.expected_course[0])

        # Try the get courses that are not there
        courses = db.browse_courses(1, 1000, 100, False)
        self.assertEquals(len(courses), 0)
        self.assertListEqual(courses, [])


if __name__ == '__main__':
    print 'Start running tests'
    unittest.main()
