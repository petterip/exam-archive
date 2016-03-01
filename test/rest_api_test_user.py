'''
Testing class for database API's user related functions.

Authors: Ari Kairala, Petteri Ponsimaa
Originally adopted from Ivan's exercise 1 test class.
'''

import unittest, hashlib
import re, base64, copy, json, server
from database_api_test_common import BaseTestCase, db
from flask import json, jsonify
from exam_archive import ExamDatabaseErrorNotFound, ExamDatabaseErrorExists
from unittest import TestCase
from resources_common import COLLECTIONJSON, PROBLEMJSON, USER_PROFILE, API_VERSION

class RestUserTestCase(BaseTestCase):
    '''
    RestUserTestCase contains user related unit tests of the database API.
    '''

    # List of user credentials in exam_archive_data_dump.sql for testing purposes
    super_user = "bigboss"
    super_pw = hashlib.sha256("ultimatepw").hexdigest()
    admin_user = "antti.admin"
    admin_pw = hashlib.sha256("qwerty1234").hexdigest()
    basic_user = "testuser"
    basic_pw = hashlib.sha256("testuser").hexdigest()
    wrong_pw = "wrong-pw"

    test_user_template_1 = { "template": {
                                "data": [{"name": "userType", "value": "super"},
                                         {"name": "name", "value": "TEST_USER"},
                                         {"name": "accessCode", "value": "qwerty123"},
                                         {"name": "archiveId", "value": 1}]
                                }
                            }
    test_user_template_2 = { "template": {
                                "data": [{"name": "userType", "value": "basic"},
                                         {"name": "name", "value": "EDIT_USER"},
                                         {"name": "accessCode", "value": "asdfg567"},
                                         {"name": "archiveId", "value": 2}]
                                }
                            }

    user_resource_url = '/exam_archive/api/users/testuser/'
    userlist_resource_url = '/exam_archive/api/users/'

    # Set a ready header for authorized admin user
    header_auth = {'Authorization': 'Basic ' + base64.b64encode(super_user + ":" + super_pw)}

    # Define a list of the sample contents of the database, so we can later compare it to the test results

    @classmethod
    def setUpClass(cls):
        print "Testing ", cls.__name__

    def test_user_not_authorized(self):
        '''
        Check that user in not able to get user list without authenticating.
        '''
        print '(' + self.test_user_not_authorized.__name__ + ')', \
            self.test_user_not_authorized.__doc__

        # Test UserList/GET
        rv = self.app.get(self.userlist_resource_url)
        assert rv.status_code == 401
        assert PROBLEMJSON in rv.mimetype

        # Test UserList/POST
        rv = self.app.post(self.userlist_resource_url)
        assert rv.status_code == 401
        assert PROBLEMJSON in rv.mimetype

        # Test User/GET
        rv = self.app.get(self.user_resource_url)
        assert rv.status_code == 401
        assert PROBLEMJSON in rv.mimetype

        # Test User/PUT
        rv = self.app.put(self.user_resource_url)
        assert rv.status_code == 401
        assert PROBLEMJSON in rv.mimetype

        # Test User/DELETE
        rv = self.app.put(self.user_resource_url)
        assert rv.status_code == 401
        assert PROBLEMJSON in rv.mimetype

        # Try to User/POST when not super user
        rv = self.app.post(self.userlist_resource_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.admin_user + ":" + self.admin_pw)})
        assert rv.status_code == 403
        assert PROBLEMJSON in rv.mimetype

        # Try to delete user, when not super user
        rv = self.app.delete(self.user_resource_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.basic_user + ":" + self.basic_pw)})
        assert rv.status_code == 403
        assert PROBLEMJSON in rv.mimetype

        # Try to get User list as basic user
        rv = self.app.get(self.userlist_resource_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.basic_user + ":" + self.basic_pw)})
        assert rv.status_code == 403
        assert PROBLEMJSON in rv.mimetype

        # Try to get User list as super user with wrong password
        rv = self.app.get(self.userlist_resource_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.super_user + ":" + self.wrong_pw)})
        assert rv.status_code == 401
        assert PROBLEMJSON in rv.mimetype

    def test_user_authorized(self):
        '''
        Check that authenticated user is able to get user list.
        '''
        print '(' + self.test_user_authorized.__name__ + ')', \
            self.test_user_authorized.__doc__

        # User authorized as super user
        rv = self.app.get(self.userlist_resource_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.super_user + ":" + self.super_pw)})
        self.assertEquals(rv.status_code,200)
        self.assertEquals(COLLECTIONJSON+";"+USER_PROFILE,rv.content_type)

    def test_user_get(self):
        '''
        Check data consistency of User/GET and UserList/GET.
        '''

        print '(' + self.test_user_get.__name__ + ')', \
            self.test_user_get.__doc__
        # Test UserList/GET
        self._user_get(self.userlist_resource_url)
        # Test single user User/GET
        self._user_get(self.user_resource_url)

    def _user_get(self, resource_url):
        '''
        Check data consistency of UserList/GET.
        '''

        # Get all the users from database
        users = db.browse_users()

        # Get all the users from API
        rv = self.app.get(resource_url, headers=self.header_auth)
        self.assertEquals(rv.status_code,200)
        self.assertEquals(COLLECTIONJSON+";"+USER_PROFILE,rv.content_type)

        input = json.loads(rv.data)
        assert input

        # Go through the data
        data = input['collection']
        items = data['items']

        self.assertEquals(data['href'], resource_url)
        self.assertEquals(data['version'], API_VERSION)

        for item in items:
            obj = self._create_dict(item['data'])
            user = db.get_user(obj['userId'])
            assert self._isIdentical(obj, user)

    def test_user_post(self):
        '''
        Check that a new user can be created.
        '''
        print '(' + self.test_user_post.__name__ + ')', \
            self.test_user_post.__doc__

        resource_url = self.userlist_resource_url
        new_user = self.test_user_template_1.copy()

        # Test UserList/POST
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(new_user))
        self.assertEquals(rv.status_code,201)

        # Post returns the address of newly created resource URL in header, in 'location'. Get the identifier of
        # the just created item, fetch it from database and compare.
        location = rv.location
        location_match = re.match('.*users/([^/]+)/', location)
        self.assertIsNotNone(location_match)
        new_id = location_match.group(1)

        # Fetch the item from database and set it to user_id_db, and convert the filled post template data above to
        # similar format by replacing the keys with post data attributes.
        user_in_db = db.get_user_by_name(new_id)
        user_posted = self._convert(new_user)

        # Compare the data in database and the post template above.
        self.assertDictContainsSubset(user_posted, user_in_db)

        # Next, try to add the same user twice - there should be conflict
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(new_user))
        self.assertEquals(rv.status_code,409)

        # Next check that by posting invalid JSON data we get status code 415
        invalid_json = "INVALID " + json.dumps(new_user)
        rv = self.app.post(resource_url, headers=self.header_auth, data=invalid_json)
        self.assertEquals(rv.status_code,415)

        # Check that template structure is validated
        invalid_json = json.dumps(new_user['template'])
        rv = self.app.post(resource_url, headers=self.header_auth, data=invalid_json)
        self.assertEquals(rv.status_code,400)

        # Check for missing required fields by removing the second row in array (user's name)
        invalid_template = copy.deepcopy(new_user)
        invalid_template['template']['data'].pop(1)
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(invalid_template))
        self.assertEquals(rv.status_code,400)

        # Check for missing required fields by removing the third row in array (accessCode)
        invalid_template = copy.deepcopy(new_user)
        invalid_template['template']['data'].pop(2)
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(invalid_template))
        self.assertEquals(rv.status_code,400)

        # Try to post template with invalid user type
        invalid_template = copy.deepcopy(new_user)
        invalid_template['template']['data'][0] = { 'name': 'userType', 'value':'INVALID'}
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(invalid_template))
        self.assertEquals(rv.status_code,400)

        # Lastly, delete the item
        rv = self.app.delete(location, headers=self.header_auth)
        self.assertEquals(rv.status_code,204)

    def test_user_put(self):
        '''
        Check that an existing user can be modified.
        '''
        print '(' + self.test_user_put.__name__ + ')', \
            self.test_user_put.__doc__

        resource_url = self.userlist_resource_url
        new_user = self.test_user_template_1
        edited_user =  self.test_user_template_2

        # First create the user
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(new_user))
        self.assertEquals(rv.status_code,201)
        location = rv.location
        self.assertIsNotNone(location)

        # Then try to edit the user
        rv = self.app.put(location, headers=self.header_auth, data=json.dumps(edited_user))
        self.assertEquals(rv.status_code,200)
        location = rv.location
        self.assertIsNotNone(location)

        # Put returns the address of newly created resource URL in header, in 'location'. Get the identifier of
        # the just created item, fetch it from database and compare.
        location = rv.location
        location_match = re.match('.*users/([^/]+)/', location)
        self.assertIsNotNone(location_match)
        new_id = location_match.group(1)

        # Fetch the item from database and set it to user_id_db, and convert the filled post template data above to
        # similar format by replacing the keys with post data attributes.
        user_in_db = db.get_user_by_name(new_id)
        user_posted = self._convert(edited_user)

        # Compare the data in database and the post template above.
        self.assertDictContainsSubset(user_posted, user_in_db)

        # Next check that by posting invalid JSON data we get status code 415
        invalid_json = "INVALID " + json.dumps(new_user)
        rv = self.app.put(location, headers=self.header_auth, data=invalid_json)
        self.assertEquals(rv.status_code,415)

        # Check that template structure is validated
        invalid_json = json.dumps(new_user['template'])
        rv = self.app.put(location, headers=self.header_auth, data=invalid_json)
        self.assertEquals(rv.status_code,400)

        # Try to post template with invalid user type
        invalid_template = copy.deepcopy(new_user)
        invalid_template['template']['data'][0] = { 'name': 'userType', 'value':'INVALID'}
        rv = self.app.put(location, headers=self.header_auth, data=json.dumps(invalid_template))
        self.assertEquals(rv.status_code,400)

        # Lastly, we delete the user
        rv = self.app.delete(location, headers=self.header_auth)
        self.assertEquals(rv.status_code,204)

    def test_user_delete(self):
        '''
        Check that user in not able to get user list without authenticating.
        '''
        print '(' + self.test_user_delete.__name__ + ')', \
            self.test_user_delete.__doc__

        # First create the user
        resource_url = self.userlist_resource_url
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(self.test_user_template_2))
        self.assertEquals(rv.status_code,201)
        location = rv.location
        self.assertIsNotNone(location)

        # Get the identifier of the just created item, fetch it from database and compare.
        location = rv.location
        location_match = re.match('.*users/([^/]+)/', location)
        self.assertIsNotNone(location_match)
        new_id = location_match.group(1)

        # Then, we delete the user
        rv = self.app.delete(location, headers=self.header_auth)
        self.assertEquals(rv.status_code,204)

        # Try to fetch the deleted user from database - expect to fail
        self.assertIsNone(db.get_user_by_name(new_id))

    def test_for_method_not_allowed(self):
        '''
        For inconsistency check for 405, method not allowed.
        '''

        print '(' + self.test_user_get.__name__ + ')', \
            self.test_user_get.__doc__

        # UserList/PUT should not exist
        rv = self.app.put(self.userlist_resource_url, headers=self.header_auth)
        self.assertEquals(rv.status_code,405)

        # UserList/DELETE should not exist
        rv = self.app.delete(self.userlist_resource_url, headers=self.header_auth)
        self.assertEquals(rv.status_code,405)

        # User/POST should not exist
        rv = self.app.post(self.user_resource_url, headers=self.header_auth)
        self.assertEquals(rv.status_code,405)

    def _isIdentical(self, api_item, db_item):
        '''
        Check whether template data corresponds to data stored in the database.
        '''

        return api_item['userId'] == db_item['user_id'] and \
               api_item['name'] == db_item['username'] and \
               api_item['accessCode'] == db_item['password'] and \
               api_item['userType'] == db_item['user_type']

    def _convert(self, template_data):
        '''
        Convert template data to a dictionary representing the format the data is saved in the database.
        '''

        trans_table = {"name":"username", "accessCode":"password", "archiveId":"archive_id", "dateModified": "date",
                       "modifierId":"modifier_id", "userId":"user_id", "userType":"user_type"}
        data = self._create_dict(template_data['template']['data'])

        db_item = {}
        for key, val in data.items():
            db_item[trans_table[key]] = val

        return db_item

    def _create_dict(self,item):
        '''
        Create a dictionary from template data for easier handling.
        '''

        dict = {}
        for f in item:
            dict[f['name']] = f['value']

        return dict

if __name__ == '__main__':
    print 'Start running tests'
    unittest.main()

