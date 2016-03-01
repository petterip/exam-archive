'''
Testing class for database API's archive related functions.

Authors: Ari Kairala, Petteri Ponsimaa
Originally adopted from Ivan's exercise 1 test class.
'''

import sqlite3, unittest, pytest

from database_api_test_common import BaseTestCase, db, db_path
from exam_archive import ExamDatabaseErrorNotFound, ExamDatabaseErrorExists


class LanguageTestCase(BaseTestCase):
    '''
    Test cases for language are not implemented as language related functions are outside of this project scope.
    '''
    pass

if __name__ == '__main__':
    print 'No tests to run'
    unittest.main()
