__authors__ = 'Petteri Ponsimaa, Ari Kairala'

import unittest, os, hashlib
import exam_archive
import server

# Path to the database file, different from the deployment db
db_path = 'db/exam_archive_test.db'
db = exam_archive.ExamArchiveDatabase(db_path)

class BaseTestCase(unittest.TestCase):
    '''
    Base class for all test classes. It implements the setUp and the tearDown
    methods inherit by the rest of test classes.
    '''

    def setUp(self):
        '''
        Clean the database (in SQLite you can remove the whole database file)
        and create a new one for loading the inital values.
        '''
        # Be sure that there is no database.
        # This specially is useful if the clean process was not success.
        if os.path.exists(db_path):
            os.remove(db_path)
        # This method load the initial values from forum_data_dump.sql
        # It creates the database if it does not exist.
        db.load_init_values()

        server.app.config['TESTING'] = True
        server.app.config.update({'DATABASE':exam_archive.ExamArchiveDatabase(db_path)})
        self.app = server.app.test_client()

    def tearDown(self):
        db.clean()
        pass

def encrypt(pw):
    return hashlib.sha256(pw).hexdigest()

if __name__ == '__main__':
    unittest.main()
else:
    # During development let the database file to be found
    if os.path.exists('../test'):
        os.chdir("../")
