'''
Testing class for database API's archive related functions.

Authors: Ari Kairala, Petteri Ponsimaa
Originally adopted from Ivan's exercise 1 test class.
'''

import unittest, hashlib
import re, base64, copy, json, server
from database_api_test_common import BaseTestCase, db
from flask import json, jsonify
from exam_archive import ExamDatabaseErrorNotFound, ExamDatabaseErrorExists
from unittest import TestCase
from resources_common import COLLECTIONJSON, PROBLEMJSON, ARCHIVE_PROFILE, API_VERSION

class RestArchiveTestCase(BaseTestCase):
    '''
    RestArchiveTestCase contains archive related unit tests of the database API.
    '''

    # List of user credentials in exam_archive_data_dump.sql for testing purposes
    super_user = "bigboss"
    super_pw = hashlib.sha256("ultimatepw").hexdigest()
    admin_user = "antti.admin"
    admin_pw = hashlib.sha256("qwerty1234").hexdigest()
    basic_user = "testuser"
    basic_pw = hashlib.sha256("testuser").hexdigest()
    wrong_pw = "wrong-pw"

    test_archive_template_1 = {"template": {
        "data": [{"name": "archiveId", "value": 4},
                 {"name": "name", "value": "Computer Science"},
                 {"name": "organisationName", "value": "OTiT"},
                 {"name": "identificationNeeded", "value": 1}]
    }
    }
    test_archive_template_2 = {"template": {
        "data": [{"name": "archiveId", "value": 4},
                 {"name": "name", "value": "Wireless Communication Engineering"},
                 {"name": "organisationName", "value": "OTiT"},
                 {"name": "identificationNeeded", "value": 0}]
    }
    }

    archivelist_resource_url = '/exam_archive/api/archives/'

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

        # Test ArchiveList/GET
        rv = self.app.get(self.archivelist_resource_url)
        assert rv.status_code == 401
        assert PROBLEMJSON in rv.mimetype

        # Try to get Archive list as super user with wrong password
        rv = self.app.get(self.archivelist_resource_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.super_user + ":" + self.wrong_pw)})
        assert rv.status_code == 401
        assert PROBLEMJSON in rv.mimetype

    def test_user_authorized(self):
        '''
        Check that authenticated user is able to get archive list.
        '''
        print '(' + self.test_user_authorized.__name__ + ')', \
            self.test_user_authorized.__doc__

        # Get Archive list as basic user
        rv = self.app.get(self.archivelist_resource_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.basic_user + ":" + self.basic_pw)})
        assert rv.status_code == 200
        assert COLLECTIONJSON in rv.mimetype

        # User authorized as super user
        rv = self.app.get(self.archivelist_resource_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.super_user + ":" + self.super_pw)})
        self.assertEquals(rv.status_code,200)
        self.assertEquals(COLLECTIONJSON+";"+ARCHIVE_PROFILE,rv.content_type)

    def test_archive_get(self):
        '''
        Check data consistency of Archive/GET and ArchiveList/GET.
        '''

        print '(' + self.test_archive_get.__name__ + ')', \
            self.test_archive_get.__doc__

        # Test ArchiveList/GET
        self._archive_get(self.archivelist_resource_url)

    def _archive_get(self, resource_url):
        '''
        Check data consistency of ArchiveList/GET.
        '''

        # Get all the archives from database
        archives = db.browse_archives()

        # Get all the archives from API
        rv = self.app.get(resource_url, headers=self.header_auth)
        self.assertEquals(rv.status_code,200)
        self.assertEquals(COLLECTIONJSON+";"+ARCHIVE_PROFILE,rv.content_type)

        input = json.loads(rv.data)
        assert input

        # Go through the data
        data = input['collection']
        items = data['items']

        self.assertEquals(data['href'], resource_url)
        self.assertEquals(data['version'], API_VERSION)

        for item in items:
            obj = self._create_dict(item['data'])
            archive = db.get_archive(obj['archiveId'])
            assert self._isIdentical(obj, archive)

    def test_archive_post(self):
        '''
        Check that a new archive can be created.
        '''
        print '(' + self.test_archive_post.__name__ + ')', \
            self.test_archive_post.__doc__

        resource_url = self.archivelist_resource_url
        new_archive = self.test_archive_template_1.copy()

        # Test ArchiveList/POST
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(new_archive))
        self.assertEquals(rv.status_code,201)

        # Post returns the address of newly created resource URL in header, in 'location'. Get the identifier of
        # the just created item, fetch it from database and compare.
        location = rv.location
        location_match = re.match('.*archives/([^/]+)/', location)
        self.assertIsNotNone(location_match)
        new_id = location_match.group(1)

        # Fetch the item from database and set it to archive_id_db, and convert the filled post template data above to
        # similar format by replacing the keys with post data attributes.
        archive_in_db = db.get_archive(new_id)
        archive_posted = self._convert(new_archive)

        # Compare the data in database and the post template above.
        self.assertDictContainsSubset(archive_posted, archive_in_db)

        # Next, try to add the same archive twice - there should be conflict
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(new_archive))
        self.assertEquals(rv.status_code,409)

        # Next check that by posting invalid JSON data we get status code 415
        invalid_json = "INVALID " + json.dumps(new_archive)
        rv = self.app.post(resource_url, headers=self.header_auth, data=invalid_json)
        self.assertEquals(rv.status_code,415)

        # Check that template structure is validated
        invalid_json = json.dumps(new_archive['template'])
        rv = self.app.post(resource_url, headers=self.header_auth, data=invalid_json)
        self.assertEquals(rv.status_code,400)

        # Check for the missing required field by removing the third row in array (archive name)
        invalid_template = copy.deepcopy(new_archive)
        invalid_template['template']['data'].pop(1)
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(invalid_template))
        self.assertEquals(rv.status_code,400)

        # Lastly, delete the item
        rv = self.app.delete(location, headers=self.header_auth)
        self.assertEquals(rv.status_code,204)

    def test_archive_put(self):
        '''
        Check that an existing archive can be modified.
        '''
        print '(' + self.test_archive_put.__name__ + ')', \
            self.test_archive_put.__doc__

        resource_url = self.archivelist_resource_url
        new_archive = self.test_archive_template_1
        edited_archive =  self.test_archive_template_2

        # First create the archive
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(new_archive))
        self.assertEquals(rv.status_code,201)
        location = rv.location
        self.assertIsNotNone(location)

        # Then try to edit the archive
        rv = self.app.put(location, headers=self.header_auth, data=json.dumps(edited_archive))
        self.assertEquals(rv.status_code,200)
        location = rv.location
        self.assertIsNotNone(location)

        # Put returns the address of newly created resource URL in header, in 'location'. Get the identifier of
        # the just created item, fetch it from database and compare.
        location = rv.location
        location_match = re.match('.*archives/([^/]+)/', location)
        self.assertIsNotNone(location_match)
        new_id = location_match.group(1)

        # Fetch the item from database and set it to archive_id_db, and convert the filled post template data above to
        # similar format by replacing the keys with post data attributes.
        archive_in_db = db.get_archive(new_id)
        archive_posted = self._convert(edited_archive)

        # Compare the data in database and the post template above.
        self.assertDictContainsSubset(archive_posted, archive_in_db)

        # Next check that by posting invalid JSON data we get status code 415
        invalid_json = "INVALID " + json.dumps(new_archive)
        rv = self.app.put(location, headers=self.header_auth, data=invalid_json)
        self.assertEquals(rv.status_code,415)

        # Check that template structure is validated
        invalid_json = json.dumps(new_archive['template'])
        rv = self.app.put(location, headers=self.header_auth, data=invalid_json)
        self.assertEquals(rv.status_code,400)

        # Lastly, we delete the archive
        rv = self.app.delete(location, headers=self.header_auth)
        self.assertEquals(rv.status_code,204)

    def test_archive_delete(self):
        '''
        Check that archive in not able to get archive list without authenticating.
        '''
        print '(' + self.test_archive_delete.__name__ + ')', \
            self.test_archive_delete.__doc__

        # First create the archive
        resource_url = self.archivelist_resource_url
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(self.test_archive_template_2))
        self.assertEquals(rv.status_code,201)
        location = rv.location
        self.assertIsNotNone(location)

        # Get the identifier of the just created item, fetch it from database and compare.
        location = rv.location
        location_match = re.match('.*archives/([^/]+)/', location)
        self.assertIsNotNone(location_match)
        new_id = location_match.group(1)

        # Then, we delete the archive
        rv = self.app.delete(location, headers=self.header_auth)
        self.assertEquals(rv.status_code,204)

        # Try to fetch the deleted archive from database - expect to fail
        self.assertIsNone(db.get_archive(new_id))



    def test_for_method_not_allowed(self):
        '''
        For inconsistency check for 405, method not allowed.
        '''

        print '(' + self.test_archive_get.__name__ + ')', \
            self.test_archive_get.__doc__

        # ArchiveList/PUT should not exist
        rv = self.app.put(self.archivelist_resource_url, headers=self.header_auth)
        self.assertEquals(rv.status_code,405)

        # ArchiveList/DELETE should not exist
        rv = self.app.delete(self.archivelist_resource_url, headers=self.header_auth)
        self.assertEquals(rv.status_code,405)

    def _isIdentical(self, api_item, db_item):
        '''
        Check whether template data corresponds to data stored in the database.
        '''

        return api_item['archiveId'] == db_item['archive_id'] and \
               api_item['name'] == db_item['archive_name'] and \
               api_item['organisationName'] == db_item['organisation_name'] and \
               api_item['identificationNeeded'] == db_item['identification_needed']

    def _convert(self, template_data):
        '''
        Convert template data to a dictionary representing the format the data is saved in the database.
        '''

        trans_table = {"name":"archive_name", "organisationName":"organisation_name", "archiveId":"archive_id", "dateModified": "date",
                       "modifierId":"modifier_id", "archiveId":"archive_id", "identificationNeeded":"identification_needed"}
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
#        assert 'No entries here so far' in rv.data

if __name__ == '__main__':
    print 'Start running tests'
    unittest.main()
