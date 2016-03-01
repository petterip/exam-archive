'''
Testing class for database API's user related functions.

Authors: Ari Kairala, Petteri Ponsimaa
Originally adopted from Ivan's exercise 1 test class.
'''

import sqlite3, unittest

from database_api_test_common import BaseTestCase, db, db_path
from exam_archive import ExamDatabaseErrorNotFound, ExamDatabaseErrorExists
from database_api_test_common import encrypt

class UserTestCase(BaseTestCase):
    '''
    UserTestCase contains user related unit tests of the database API.
    '''

    # Define a list of the sample contents of the database, so we can later compare it to the test results
    expected_users = [
        {'username': u'bigboss', 'archive_id': 1, 'user_id': 1, 'user_type': u'super', 'last_modified': u'2015-02-25',
         'password': encrypt('ultimatepw'), 'modifier_id': None},

        {'username': u'antti.admin', 'archive_id': 1, 'user_id': 2, 'user_type': u'admin',
         'last_modified': u'2015-02-25', 'password': encrypt('qwerty1234'), 'modifier_id': u'1'},

        {'username': 'testuser', 'archive_id': 1, 'user_id': 3, 'user_type': u'basic', 'last_modified': u'2015-02-25',
         'password': encrypt('testuser'), 'modifier_id': u'1'}]

    user_initial_size = 3

    @classmethod
    def setUpClass(cls):
        print "Testing ", cls.__name__

    def test_user_table_created(self):
        '''
        Checks that the user table initially contains the expected rows from exam_user_data_dump.sql so we
        are ready to run the following unit tests.
        '''
        print '(' + self.test_user_table_created.__name__ + ')', \
            self.test_user_table_created.__doc__

        # Create the SQL Statement
        keys_on = 'PRAGMA foreign_keys = ON'
        query1 = 'SELECT * FROM user'

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
            # Assert that we do what was expected (3 rows)
            self.assertEquals(len(users), len(self.expected_users))

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
        query = 'SELECT * FROM user WHERE user_id = 1'

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
            user = db._create_object(row)
            self.assertDictContainsSubset(user, self.expected_users[0])

    def test_create_user(self):
        '''
        Test that new users can be created of type 'basic', 'admin' and 'super'
        '''
        print '(' + self.test_create_user.__name__ + ')', \
            self.test_create_user.__doc__

        # Test creating a user with all three types
        user_id_1 = db.create_user('newuser1', encrypt('qwerty1234'), user_type='super', archive_id=None, modifier_id=None)
        self.assertIsNotNone(user_id_1)
        user_id_2 = db.create_user('newuser2', '', user_type='basic', archive_id=1, modifier_id=1)
        self.assertIsNotNone(user_id_2)
        user_id_3 = db.create_user('newuser3', encrypt('qwerty1234'), user_type='admin', archive_id=2)
        self.assertIsNotNone(user_id_3)

        # Get the expected modified message
        new_user = [{'username': u'newuser1', 'archive_id': None, 'user_id': user_id_1, 'user_type': u'super',
                     'password': encrypt('qwerty1234'), 'modifier_id': None},

                    {'username': u'newuser2', 'archive_id': 1, 'user_id': user_id_2, 'user_type': u'basic',
                     'password': '', 'modifier_id': u'1'},

                    {'username': u'newuser3', 'archive_id': 2, 'user_id': user_id_3, 'user_type': u'admin',
                     'password': encrypt('qwerty1234'), 'modifier_id': None}]


        # Create the SQL Statement
        keys_on = 'PRAGMA foreign_keys = ON'
        query = 'SELECT * FROM user WHERE user_id = ? OR user_id = ? OR user_id = ? ORDER BY user_id'

        # Connects to the database.
        con = sqlite3.connect(db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)
            #Execute main SQL Statement
            cur.execute(query, (user_id_1, user_id_2, user_id_3))
            #Extrac the row
            row = cur.fetchall()
            # Let's check that there was at least one matching row
            self.assertIsNotNone(row)
            self.assertEquals(len(row), len(new_user))

            #Test that rows were created as expected
            user = db._create_object(row[0])
            self.assertDictContainsSubset(new_user[0], user)
            user = db._create_object(row[1])
            self.assertDictContainsSubset(new_user[1], user)
            user = db._create_object(row[2])
            self.assertDictContainsSubset(new_user[2], user)

        # Check for value error: "User type is not basic, admin or super"
        self.assertRaises(ValueError, db.create_user, 'hyperuser', '', user_type='HYPER', archive_id=1, modifier_id=1)

        # Check the two users can not be created with the same username: "The given username already exists"
        self.assertRaises(ExamDatabaseErrorExists, db.create_user, 'newuser1', encrypt('qwerty1234'))

        # Check for foreign key constraints: "Modifier does not exist"
        self.assertRaises(ExamDatabaseErrorNotFound, db.create_user, 'newuser1', '', 'super', 1, 999)

    def test_edit_user(self):
        '''
        Test that users can be edited (types 'basic', 'admin' and 'super')
        '''
        print '(' + self.test_create_user.__name__ + ')', \
            self.test_create_user.__doc__

        # Create first test users of all three types
        user_id_1 = db.create_user('edituser1', 'qwerty1234', user_type='super', archive_id=None, modifier_id=None)
        self.assertIsNotNone(user_id_1)
        user_id_2 = db.create_user('edituser2', '', user_type='basic', archive_id=1, modifier_id=1)
        self.assertIsNotNone(user_id_2)
        user_id_3 = db.create_user('edituser3', 'qwerty1234', user_type='admin', archive_id=2)
        self.assertIsNotNone(user_id_3)

        # Test modifying users of all three types
        user_id_1 = db.edit_user(user_id_1, 'edituser1', 'Qwerty1234', user_type='basic', archive_id=1, modifier_id=1)
        self.assertIsNotNone(user_id_1)
        user_id_2 = db.edit_user(user_id_2, 'edituser2', '', user_type='admin', archive_id=1, modifier_id=None)
        self.assertIsNotNone(user_id_2)
        user_id_3 = db.edit_user(user_id_3, 'edituser3', 'qWerty1234', user_type='super', archive_id=2)
        self.assertIsNotNone(user_id_3)

        # Get the expected modified message
        new_user = [{'username': u'edituser1', 'archive_id': 1, 'user_id': user_id_1, 'user_type': u'basic',
                     'password': u'Qwerty1234', 'modifier_id': u'1'},

                    {'username': u'edituser2', 'archive_id': 1, 'user_id': user_id_2, 'user_type': u'admin',
                     'password': '', 'modifier_id': None},

                    {'username': u'edituser3', 'archive_id': 2, 'user_id': user_id_3, 'user_type': u'super',
                     'password': u'qWerty1234', 'modifier_id': None}]


        # Create the SQL Statement
        keys_on = 'PRAGMA foreign_keys = ON'
        query = 'SELECT * FROM user WHERE user_id = ? OR user_id = ? OR user_id = ? ORDER BY user_id'

        # Connects to the database.
        con = sqlite3.connect(db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)
            #Execute main SQL Statement
            cur.execute(query, (user_id_1, user_id_2, user_id_3))
            #Extrac the row
            row = cur.fetchall()
            # Let's check that there was at least one matching row
            self.assertIsNotNone(row)
            self.assertEquals(len(row), len(new_user))

            #Test that rows were created as expected
            user = db._create_object(row[0])
            self.assertDictContainsSubset(new_user[0], user)
            user = db._create_object(row[1])
            self.assertDictContainsSubset(new_user[1], user)
            user = db._create_object(row[2])
            self.assertDictContainsSubset(new_user[2], user)

        # Check for value error: "User type is not basic, admin or super"
        self.assertRaises(ValueError, db.edit_user, user_id_2, 'hyperuser', '', user_type='HYPER', archive_id=1, modifier_id=1)

        # Check the two users can not be created with the same username: "The given username already exists"
        self.assertRaises(ExamDatabaseErrorExists, db.edit_user, user_id_3, 'edituser1', 'qwerty1234')

        # Check for foreign key constraints: "Modifier does not exist"
        self.assertRaises(ExamDatabaseErrorNotFound, db.create_user, 'newuser1', '', 'super', 1, 999)

    def test_remove_user(self):
        '''
        Test that an user can be deleted
        '''
        print '(' + self.test_remove_user.__name__ + ')', \
            self.test_remove_user.__doc__

        user_id = db.create_user('keijo', 'dfdf245rf23')

        # Delete the user we created
        deleted_users_id = db.remove_user(user_id)
        self.assertEquals(deleted_users_id, True)

        # Try to delete again the user we created, should fail
        ret = db.remove_user(user_id)
        self.assertEquals(ret, False)

    def test_get_user(self):
        '''
        Test get_user with id 1
        '''
        user_id = 2
        print '(' + self.test_get_user.__name__ + ')', \
            self.test_get_user.__doc__

        # Test an existing user
        user = db.get_user(user_id)
        self.assertDictContainsSubset(user, self.expected_users[1])

    def test_get_user_nonexisting(self):
        '''
        Test get_user with non-existing id of 999 and non-existing name of 'XYZ'
        '''
        no_user_id = 999
        no_user_name = 'XYZ'

        print '(' + self.test_get_user_nonexisting.__name__ + ')', \
            self.test_get_user_nonexisting.__doc__

        # Test with an non-existing user
        message = db.get_user(no_user_id)
        self.assertIsNone(message)

        # Test with an non-existing user
        message = db.get_user_by_name('NonExistingUserXYZ')
        self.assertIsNone(message)

        # Test with an non-existing user of None
        message = db.get_user_by_name(None)
        self.assertIsNone(message)

    def test_get_user_by_name(self):
        '''
        Test get_user_by_name with name 'Tero Testaaja'
        '''
        print '(' + self.test_get_user.__name__ + ')', \
            self.test_get_user.__doc__

        # Test an existing user
        user = db.get_user_by_name('bigboss')
        self.assertDictContainsSubset(user, self.expected_users[0])

    def test_authorize_user(self):

        print '(' + self.test_authorize_user.__name__ + ')', \
            self.test_authorize_user.__doc__

        # Test authorize_user with correct username 'bigboss' and correct password 'ultimatepw'
        user = db.authorize_user('bigboss', encrypt('ultimatepw'))
        self.assertIsNotNone(user)
        self.assertEquals(user, self.expected_users[0]['user_id'])

        # Test authorize_user with correct username 'bigboss' and incorrect password 'invalidpw123'
        user = db.authorize_user('bigboss', 'invalidpw123')
        self.assertIsNone(user)

        # Test authorize_user with an non-existing user of None
        user = db.authorize_user(None, None)
        self.assertIsNone(user)

    def test_user_has_access(self):
        '''
        Test user_has_access
        '''
        print '(' + self.test_user_has_access.__name__ + ')', \
            self.test_user_has_access.__doc__

        # Test user_has_access with usertype super
        user = db.user_has_access('1', 'super')
        self.assertEquals(user, True)

        # Test user_has_access with usertype basic, when user has access to the archive
        user = db.user_has_access('3', '1')
        self.assertEquals(user, True)

        # Test user_has_access with usertype basic, when user has not access to the archive
        user = db.user_has_access('3', '4')
        self.assertEquals(user, False)

    def test_browse_users(self):
        '''
        Test that browse_users works correctly by fetching 3 users, only one and non-existing users
        '''
        # (self, limit=-1, offset=0, offset_represents_ids=False):

        print '(' + self.test_browse_users.__name__ + ')', self.test_browse_users.__doc__

        # Try browsing the user with parameter combinations testing the limits. First, check that we get the same
        # correct number of users with the contents in expected_users list.
        users = db.browse_users()
        self.assertEquals(len(users), len(self.expected_users))
        self.assertListEqual(users, self.expected_users)

        # The same as above but with default parameters
        users = db.browse_users(limit=-1, offset=0)
        self.assertEquals(len(users), len(self.expected_users))
        self.assertListEqual(users, self.expected_users)

        # Get only the second row, using offset as the ID of the user (essentially same as get_user(1) )
        users = db.browse_users(limit=1, offset=1, offset_represents_ids=True)
        self.assertEquals(len(users), 1)
        self.assertDictEqual(users[0], self.expected_users[0])

        # Try the get users that are not there
        users = db.browse_users(1000, 100, False)
        self.assertEquals(len(users), 0)
        self.assertListEqual(users, [])

if __name__ == '__main__':
    print 'Start running tests'
    unittest.main()
