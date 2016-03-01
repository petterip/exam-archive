'''
Testing class for database API's exam related functions.

Authors: Ari Kairala, Petteri Ponsimaa
Originally adopted from Ivan's exercise 1 test class.
'''

import unittest, hashlib
import re, base64, copy, json, server
from database_api_test_common import BaseTestCase, db
from flask import json, jsonify
from exam_archive import ExamDatabaseErrorNotFound, ExamDatabaseErrorExists
from unittest import TestCase
from resources_common import COLLECTIONJSON, PROBLEMJSON, EXAM_PROFILE, API_VERSION

class RestExamTestCase(BaseTestCase):
    '''
    RestExamTestCase contains exam related unit tests of the database API.
    '''

    # List of user credentials in exam_archive_data_dump.sql for testing purposes
    super_user = "bigboss"
    super_pw = hashlib.sha256("ultimatepw").hexdigest()
    admin_user = "antti.admin"
    admin_pw = hashlib.sha256("qwerty1234").hexdigest()
    basic_user = "testuser"
    basic_pw = hashlib.sha256("testuser").hexdigest()
    wrong_pw = "wrong-pw"

    test_exam_template_1 = {"template": {
        "data": [
                 {"name": "examinerId", "value": 1},
                 {"name": "inLanguage", "value": 'fi'},
                 {"name": "date", "value": "2013-03-21"},
                 {"name": "courseId", "value": 1},
                 {"name": "associatedMedia", "value": "810136P_exam2013-02-21.pdf"}]
    }
    }
    test_exam_template_2 = {"template": {
        "data": [
                 {"name": "examinerId", "value": 2},
                 {"name": "inLanguage", "value": 'en'},
                 {"name": "date", "value": "2013-04-29"},
                 {"name": "courseId", "value": 1},
                 {"name": "associatedMedia", "value": "810136P_exam2013-04-29.pdf"}]
    }
    }

    exam_resource_url = '/exam_archive/api/archives/1/courses/1/exams/1/'
    examlist_resource_url = '/exam_archive/api/archives/1/courses/1/exams/'
    examlist_resource_not_allowed_url = '/exam_archive/api/archives/2/courses/1/exams/'

    # Set a ready header for authorized admin user
    header_auth = {'Authorization': 'Basic ' + base64.b64encode(super_user + ":" + super_pw)}

    # Define a list of the sample contents of the database, so we can later compare it to the test results

    @classmethod
    def setUpClass(cls):
        print "Testing ", cls.__name__

    def test_user_not_authorized(self):
        '''
        Check that user in not able to get exam list without authenticating.
        '''
        print '(' + self.test_user_not_authorized.__name__ + ')', \
            self.test_user_not_authorized.__doc__

        # Test ExamList/GET
        rv = self.app.get(self.examlist_resource_url)
        assert rv.status_code == 401
        assert PROBLEMJSON in rv.mimetype

        # Test ExamList/POST
        rv = self.app.post(self.examlist_resource_url)
        assert rv.status_code == 401
        assert PROBLEMJSON in rv.mimetype

        # Test Exam/GET
        rv = self.app.get(self.exam_resource_url)
        assert rv.status_code == 401
        assert PROBLEMJSON in rv.mimetype

        # Test Exam/PUT
        rv = self.app.put(self.exam_resource_url)
        assert rv.status_code == 401
        assert PROBLEMJSON in rv.mimetype

        # Test Exam/DELETE
        rv = self.app.put(self.exam_resource_url)
        assert rv.status_code == 401
        assert PROBLEMJSON in rv.mimetype

        # Try to Exam/POST when not admin or super user
        rv = self.app.post(self.examlist_resource_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.basic_user + ":" + self.basic_pw)})
        assert rv.status_code == 403
        assert PROBLEMJSON in rv.mimetype

        # Try to delete Exam, when not admin or super user
        rv = self.app.delete(self.exam_resource_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.basic_user + ":" + self.basic_pw)})
        assert rv.status_code == 403
        assert PROBLEMJSON in rv.mimetype

        # Try to get Exam list as basic user
        rv = self.app.get(self.examlist_resource_not_allowed_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.basic_user + ":" + self.basic_pw)})
        assert rv.status_code == 403
        assert PROBLEMJSON in rv.mimetype

        # Try to get Exam list as super user with wrong password
        rv = self.app.get(self.examlist_resource_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.super_user + ":" + self.wrong_pw)})
        assert rv.status_code == 401
        assert PROBLEMJSON in rv.mimetype

    def test_user_authorized(self):
        '''
        Check that authenticated user is able to get exam list.
        '''
        print '(' + self.test_user_authorized.__name__ + ')', \
            self.test_user_authorized.__doc__

        # Get Exam list as basic user from archive where the user has access to
        rv = self.app.get(self.examlist_resource_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.basic_user + ":" + self.basic_pw)})
        self.assertEquals(rv.status_code,200)
        self.assertEquals(COLLECTIONJSON+";"+EXAM_PROFILE,rv.content_type)

        # User authorized as super user
        rv = self.app.get(self.examlist_resource_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.super_user + ":" + self.super_pw)})
        self.assertEquals(rv.status_code,200)
        self.assertEquals(COLLECTIONJSON+";"+EXAM_PROFILE,rv.content_type)

    def test_exam_get(self):
        '''
        Check data consistency of Exam/GET and ExamList/GET.
        '''

        print '(' + self.test_exam_get.__name__ + ')', \
            self.test_exam_get.__doc__
        # Test ExamList/GET
        self._exam_get(self.examlist_resource_url)
        # Test single exam Exam/GET
        self._exam_get(self.exam_resource_url)

    def _exam_get(self, resource_url):
        '''
        Check data consistency of ExamList/GET.
        '''

        # Get all the exams from database
        exams = db.browse_exams(1)

        # Get all the exams from API
        rv = self.app.get(resource_url, headers=self.header_auth)
        self.assertEquals(rv.status_code,200)
        self.assertEquals(COLLECTIONJSON+";"+EXAM_PROFILE,rv.content_type)

        input = json.loads(rv.data)
        assert input

        # Go through the data
        data = input['collection']
        items = data['items']

        self.assertEquals(data['href'], resource_url)
        self.assertEquals(data['version'], API_VERSION)

        for item in items:
            obj = self._create_dict(item['data'])
            exam = db.get_exam(obj['examId'])
            assert self._isIdentical(obj, exam)

    def test_exam_post(self):
        '''
        Check that a new exam can be created.
        '''
        print '(' + self.test_exam_post.__name__ + ')', \
            self.test_exam_post.__doc__

        resource_url = self.examlist_resource_url
        new_exam = self.test_exam_template_1.copy()

        # Test ExamList/POST
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(new_exam))
        self.assertEquals(rv.status_code,201)

        # Post returns the address of newly created resource URL in header, in 'location'. Get the identifier of
        # the just created item, fetch it from database and compare.
        location = rv.location
        location_match = re.match('.*exams/([^/]+)/', location)
        self.assertIsNotNone(location_match)
        new_id = location_match.group(1)

        # Fetch the item from database and set it to exam_id_db, and convert the filled post template data above to
        # similar format by replacing the keys with post data attributes.
        exam_in_db = db.get_exam(new_id)
        exam_posted = self._convert(new_exam)

        # Compare the data in database and the post template above.
        self.assertDictContainsSubset(exam_posted, exam_in_db)

        # Next, try to add the same exam twice - there should be conflict
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(new_exam))
        self.assertEquals(rv.status_code,409)

        # Next check that by posting invalid JSON data we get status code 415
        invalid_json = "INVALID " + json.dumps(new_exam)
        rv = self.app.post(resource_url, headers=self.header_auth, data=invalid_json)
        self.assertEquals(rv.status_code,415)

        # Check that template structure is validated
        invalid_json = json.dumps(new_exam['template'])
        rv = self.app.post(resource_url, headers=self.header_auth, data=invalid_json)
        self.assertEquals(rv.status_code,400)

        # Check for missing required fields by removing the first row in array (date)
        invalid_template = copy.deepcopy(new_exam)
        invalid_template['template']['data'].pop(2)
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(invalid_template))
        self.assertEquals(rv.status_code,400)

        # Lastly, delete the item
        rv = self.app.delete(location, headers=self.header_auth)
        self.assertEquals(rv.status_code,204)

    def test_exam_put(self):
        '''
        Check that an existing exam can be modified.
        '''
        print '(' + self.test_exam_put.__name__ + ')', \
            self.test_exam_put.__doc__

        resource_url = self.examlist_resource_url
        new_exam = self.test_exam_template_1
        edited_exam =  self.test_exam_template_2

        # First create the exam
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(new_exam))
        self.assertEquals(rv.status_code,201)
        location = rv.location
        self.assertIsNotNone(location)

        # Then try to edit the exam
        rv = self.app.put(location, headers=self.header_auth, data=json.dumps(edited_exam))
        self.assertEquals(rv.status_code,200)
        location = rv.location
        self.assertIsNotNone(location)

        # Put returns the address of newly created resource URL in header, in 'location'. Get the identifier of
        # the just created item, fetch it from database and compare.
        location = rv.location
        location_match = re.match('.*exams/([^/]+)/', location)
        self.assertIsNotNone(location_match)
        new_id = location_match.group(1)

        # Fetch the item from database and set it to exam_id_db, and convert the filled post template data above to
        # similar format by replacing the keys with post data attributes.
        exam_in_db = db.get_exam(new_id)
        exam_posted = self._convert(edited_exam)

        # Compare the data in database and the post template above.
        self.assertDictContainsSubset(exam_posted, exam_in_db)

        # Next check that by posting invalid JSON data we get status code 415
        invalid_json = "INVALID " + json.dumps(new_exam)
        rv = self.app.put(location, headers=self.header_auth, data=invalid_json)
        self.assertEquals(rv.status_code,415)

        # Check that template structure is validated
        invalid_json = json.dumps(new_exam['template'])
        rv = self.app.put(location, headers=self.header_auth, data=invalid_json)
        self.assertEquals(rv.status_code,400)

        # Lastly, we delete the exam
        rv = self.app.delete(location, headers=self.header_auth)
        self.assertEquals(rv.status_code,204)

    def test_exam_delete(self):
        '''
        Check that exam in not able to get exam list without authenticating.
        '''
        print '(' + self.test_exam_delete.__name__ + ')', \
            self.test_exam_delete.__doc__

        # First create the exam
        resource_url = self.examlist_resource_url
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(self.test_exam_template_2))
        self.assertEquals(rv.status_code,201)
        location = rv.location
        self.assertIsNotNone(location)

        print "Test2"
        # Get the identifier of the just created item, fetch it from database and compare.
        location = rv.location
        location_match = re.match('.*exams/([^/]+)/', location)
        self.assertIsNotNone(location_match)
        new_id = location_match.group(1)

        print "Test3"
        # Then, we delete the exam
        rv = self.app.delete(location, headers=self.header_auth)
        self.assertEquals(rv.status_code,204)

        print "Test2"

        # Try to fetch the deleted exam from database - expect to fail
        self.assertIsNone(db.get_exam(new_id))

    def test_for_method_not_allowed(self):
        '''
        For inconsistency check for 405, method not allowed.
        '''

        print '(' + self.test_exam_get.__name__ + ')', \
            self.test_exam_get.__doc__

        # examList/PUT should not exist
        rv = self.app.put(self.examlist_resource_url, headers=self.header_auth)
        self.assertEquals(rv.status_code,405)

        # examList/DELETE should not exist
        rv = self.app.delete(self.examlist_resource_url, headers=self.header_auth)
        self.assertEquals(rv.status_code,405)

        # exam/POST should not exist
        rv = self.app.post(self.exam_resource_url, headers=self.header_auth)
        self.assertEquals(rv.status_code,405)

    def _isIdentical(self, api_item, db_item):
        '''
        Check whether template data corresponds to data stored in the database.
        '''

        return api_item['examinerId'] == db_item['examiner_id'] and \
               api_item['inLanguage'] == db_item['language_id'] and \
               api_item['date'] == db_item['date'] and \
               api_item['examId'] == db_item['exam_id'] and \
               api_item['courseId'] == db_item['course_id'] and \
               api_item['associatedMedia'] == db_item['file_attachment']

    def _convert(self, template_data):
        '''
        Convert template data to a dictionary representing the format the data is saved in the database.
        '''

        trans_table = {"examinerId":"examiner_id", "inLanguage":"language_id", "date":"date", "examId":"exam_id",
                       "courseId":"course_id", "associatedMedia":"file_attachment"}
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
