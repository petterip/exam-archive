'''
Testing class for database API's course related functions.

Authors: Ari Kairala, Petteri Ponsimaa
Originally adopted from Ivan's exercise 1 test class.
'''

import unittest, hashlib
import re, base64, copy, json, server
from database_api_test_common import BaseTestCase, db
from flask import json, jsonify
from exam_archive import ExamDatabaseErrorNotFound, ExamDatabaseErrorExists
from unittest import TestCase
from resources_common import COLLECTIONJSON, PROBLEMJSON, COURSE_PROFILE, API_VERSION

class RestCourseTestCase(BaseTestCase):
    '''
    RestCourseTestCase contains course related unit tests of the database API.
    '''

    # List of user credentials in exam_archive_data_dump.sql for testing purposes
    super_user = "bigboss"
    super_pw = hashlib.sha256("ultimatepw").hexdigest()
    admin_user = "antti.admin"
    admin_pw = hashlib.sha256("qwerty1234").hexdigest()
    basic_user = "testuser"
    basic_pw = hashlib.sha256("testuser").hexdigest()
    wrong_pw = "wrong-pw"

    test_course_template_1 = {"template": {
        "data": [
                 {"name": "archiveId", "value": 1},
                 {"name": "courseCode", "value": "810136P"},
                 {"name": "name", "value": "Johdatus tietojenk\u00e4sittelytieteisiin"},
                 {"name": "description", "value": "Lorem ipsum"},
                 {"name": "inLanguage", "value": "fi"},
                 {"name": "creditPoints", "value": 4},
                 {"name": "teacherId", "value": 1}]
    }
    }
    test_course_template_2 = {"template": {
        "data": [
                 {"name": "archiveId", "value": 1},
                 {"name": "courseCode", "value": "810137P"},
                 {"name": "name", "value": "Introduction to Information Processing Sciences"},
                 {"name": "description", "value": "Aaa Bbbb"},
                 {"name": "inLanguage", "value": "en"},
                 {"name": "creditPoints", "value": 5},
                 {"name": "teacherId", "value": 2}]
    }
    }

    course_resource_url =               '/exam_archive/api/archives/1/courses/1/'
    course_resource_not_allowed_url =   '/exam_archive/api/archives/2/courses/1/'
    courselist_resource_url =           '/exam_archive/api/archives/1/courses/'

    # Set a ready header for authorized admin user
    header_auth = {'Authorization': 'Basic ' + base64.b64encode(super_user + ":" + super_pw)}

    # Define a list of the sample contents of the database, so we can later compare it to the test results

    @classmethod
    def setUpClass(cls):
        print "Testing ", cls.__name__

    def test_user_not_authorized(self):
        '''
        Check that user in not able to get course list without authenticating.
        '''
        print '(' + self.test_user_not_authorized.__name__ + ')', \
            self.test_user_not_authorized.__doc__

        # Test CourseList/GET
        rv = self.app.get(self.courselist_resource_url)
        self.assertEquals(rv.status_code,401)
        self.assertEquals(PROBLEMJSON,rv.mimetype)

        # Test CourseList/POST
        rv = self.app.post(self.courselist_resource_url)
        self.assertEquals(rv.status_code,401)
        self.assertEquals(PROBLEMJSON,rv.mimetype)

        # Test Course/GET
        rv = self.app.get(self.course_resource_url)
        self.assertEquals(rv.status_code,401)
        self.assertEquals(PROBLEMJSON,rv.mimetype)

        # Test Course/PUT
        rv = self.app.put(self.course_resource_url)
        self.assertEquals(rv.status_code,401)
        self.assertEquals(PROBLEMJSON,rv.mimetype)

        # Test Course/DELETE
        rv = self.app.put(self.course_resource_url)
        self.assertEquals(rv.status_code,401)
        self.assertEquals(PROBLEMJSON,rv.mimetype)

        # Try to Course/POST when not admin or super user
        rv = self.app.post(self.courselist_resource_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.basic_user + ":" + self.basic_pw)})
        self.assertEquals(rv.status_code,403)
        self.assertEquals(PROBLEMJSON,rv.mimetype)

        # Try to delete course, when not admin or super user
        rv = self.app.delete(self.course_resource_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.basic_user + ":" + self.basic_pw)})
        self.assertEquals(rv.status_code,403)
        self.assertEquals(PROBLEMJSON,rv.mimetype)

        # Try to get Course list as basic user from unallowed archive
        rv = self.app.get(self.course_resource_not_allowed_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.basic_user + ":" + self.basic_pw)})
        self.assertEquals(rv.status_code,403)
        self.assertEquals(PROBLEMJSON,rv.mimetype)

        # Try to get Course list as super user with wrong password
        rv = self.app.get(self.courselist_resource_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.super_user + ":" + self.wrong_pw)})
        self.assertEquals(rv.status_code,401)
        self.assertEquals(PROBLEMJSON,rv.mimetype)

    def test_user_authorized(self):
        '''
        Check that authenticated user is able to get course list.
        '''
        print '(' + self.test_user_authorized.__name__ + ')', \
            self.test_user_authorized.__doc__

        # Try to get Course list as basic user from the correct archive
        rv = self.app.get(self.course_resource_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.basic_user + ":" + self.basic_pw)})
        self.assertEquals(rv.status_code,200)
        self.assertEquals(COLLECTIONJSON+";"+COURSE_PROFILE,rv.content_type)

        # User authorized as super user
        rv = self.app.get(self.courselist_resource_url, headers={'Authorization': 'Basic ' + \
                                                                base64.b64encode(self.super_user + ":" + self.super_pw)})
        self.assertEquals(rv.status_code,200)
        self.assertEquals(COLLECTIONJSON+";"+COURSE_PROFILE,rv.content_type)

    def test_course_get(self):
        '''
        Check data consistency of Course/GET and CourseList/GET.
        '''

        print '(' + self.test_course_get.__name__ + ')', \
            self.test_course_get.__doc__
        # Test CourseList/GET
        self._course_get(self.courselist_resource_url)
        # Test single course Course/GET
        self._course_get(self.course_resource_url)

    def _course_get(self, resource_url):
        '''
        Check data consistency of CourseList/GET.
        '''

        # Get all the courses from database
        courses = db.browse_courses(1)

        # Get all the courses from API
        rv = self.app.get(resource_url, headers=self.header_auth)
        self.assertEquals(rv.status_code,200)
        self.assertEquals(COLLECTIONJSON+";"+COURSE_PROFILE,rv.content_type)

        input = json.loads(rv.data)
        assert input

        # Go through the data
        data = input['collection']
        items = data['items']

        self.assertEquals(data['href'], resource_url)
        self.assertEquals(data['version'], API_VERSION)

        for item in items:
            obj = self._create_dict(item['data'])
            course = db.get_course(obj['courseId'])
            assert self._isIdentical(obj, course)

    def test_course_post(self):
        '''
        Check that a new course can be created.
        '''
        print '(' + self.test_course_post.__name__ + ')', \
            self.test_course_post.__doc__

        resource_url = self.courselist_resource_url
        new_course = self.test_course_template_1.copy()

        # Test CourseList/POST
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(new_course))
        self.assertEquals(rv.status_code,201)

        # Post returns the address of newly created resource URL in header, in 'location'. Get the identifier of
        # the just created item, fetch it from database and compare.
        location = rv.location
        location_match = re.match('.*courses/([^/]+)/', location)
        self.assertIsNotNone(location_match)
        new_id = location_match.group(1)

        # Fetch the item from database and set it to course_id_db, and convert the filled post template data above to
        # similar format by replacing the keys with post data attributes.
        course_in_db = db.get_course(new_id)
        course_posted = self._convert(new_course)

        # Compare the data in database and the post template above.
        self.assertDictContainsSubset(course_posted, course_in_db)

        # Next, try to add the same course twice - there should be conflict
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(new_course))
        self.assertEquals(rv.status_code,409)

        # Next check that by posting invalid JSON data we get status code 415
        invalid_json = "INVALID " + json.dumps(new_course)
        rv = self.app.post(resource_url, headers=self.header_auth, data=invalid_json)
        self.assertEquals(rv.status_code,415)

        # Check that template structure is validated
        invalid_json = json.dumps(new_course['template'])
        rv = self.app.post(resource_url, headers=self.header_auth, data=invalid_json)
        self.assertEquals(rv.status_code,400)

        # Check for the missing required field by removing the third row in array (course name)
        invalid_template = copy.deepcopy(new_course)
        invalid_template['template']['data'].pop(2)
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(invalid_template))
        self.assertEquals(rv.status_code,400)

        # Lastly, delete the item
        rv = self.app.delete(location, headers=self.header_auth)
        self.assertEquals(rv.status_code,204)

    def test_course_put(self):
        '''
        Check that an existing course can be modified.
        '''
        print '(' + self.test_course_put.__name__ + ')', \
            self.test_course_put.__doc__

        resource_url = self.courselist_resource_url
        new_course = self.test_course_template_1
        edited_course =  self.test_course_template_2

        # First create the course
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(new_course))
        self.assertEquals(rv.status_code,201)
        location = rv.location
        self.assertIsNotNone(location)

        # Then try to edit the course
        rv = self.app.put(location, headers=self.header_auth, data=json.dumps(edited_course))
        self.assertEquals(rv.status_code,200)
        location = rv.location
        self.assertIsNotNone(location)

        # Put returns the address of newly created resource URL in header, in 'location'. Get the identifier of
        # the just created item, fetch it from database and compare.
        location = rv.location
        location_match = re.match('.*courses/([^/]+)/', location)
        self.assertIsNotNone(location_match)
        new_id = location_match.group(1)

        # Fetch the item from database and set it to course_id_db, and convert the filled post template data above to
        # similar format by replacing the keys with post data attributes.
        course_in_db = db.get_course(new_id)
        course_posted = self._convert(edited_course)

        # Compare the data in database and the post template above.
        self.assertDictContainsSubset(course_posted, course_in_db)

        # Next check that by posting invalid JSON data we get status code 415
        invalid_json = "INVALID " + json.dumps(new_course)
        rv = self.app.put(location, headers=self.header_auth, data=invalid_json)
        self.assertEquals(rv.status_code,415)

        # Check that template structure is validated
        invalid_json = json.dumps(new_course['template'])
        rv = self.app.put(location, headers=self.header_auth, data=invalid_json)
        self.assertEquals(rv.status_code,400)

        # Lastly, we delete the course
        rv = self.app.delete(location, headers=self.header_auth)
        self.assertEquals(rv.status_code,204)

    def test_course_delete(self):
        '''
        Check that course in not able to get course list without authenticating.
        '''
        print '(' + self.test_course_delete.__name__ + ')', \
            self.test_course_delete.__doc__

        # First create the course
        resource_url = self.courselist_resource_url
        rv = self.app.post(resource_url, headers=self.header_auth, data=json.dumps(self.test_course_template_2))
        self.assertEquals(rv.status_code,201)
        location = rv.location
        self.assertIsNotNone(location)

        # Get the identifier of the just created item, fetch it from database and compare.
        location = rv.location
        location_match = re.match('.*courses/([^/]+)/', location)
        self.assertIsNotNone(location_match)
        new_id = location_match.group(1)

        # Then, we delete the course
        rv = self.app.delete(location, headers=self.header_auth)
        self.assertEquals(rv.status_code,204)

        # Try to fetch the deleted course from database - expect to fail
        self.assertIsNone(db.get_course(new_id))

    def test_for_method_not_allowed(self):
        '''
        For inconsistency check for 405, method not allowed.
        '''

        print '(' + self.test_course_get.__name__ + ')', \
            self.test_course_get.__doc__

        # CourseList/PUT should not exist
        rv = self.app.put(self.courselist_resource_url, headers=self.header_auth)
        self.assertEquals(rv.status_code,405)

        # CourseList/DELETE should not exist
        rv = self.app.delete(self.courselist_resource_url, headers=self.header_auth)
        self.assertEquals(rv.status_code,405)

        # Course/POST should not exist
        rv = self.app.post(self.course_resource_url, headers=self.header_auth)
        self.assertEquals(rv.status_code,405)

    def _isIdentical(self, api_item, db_item):
        '''
        Check whether template data corresponds to data stored in the database.
        '''

        return api_item['courseId'] == db_item['course_id'] and \
               api_item['name'] == db_item['course_name'] and \
               api_item['archiveId'] == db_item['archive_id'] and \
               api_item['description'] == db_item['description'] and \
               api_item['inLanguage'] == db_item['language_id'] and \
               api_item['creditPoints'] == db_item['credit_points'] and \
               api_item['courseCode'] == db_item['course_code']

    def _convert(self, template_data):
        '''
        Convert template data to a dictionary representing the format the data is saved in the database.
        '''

        trans_table = {"name":"course_name", "url":"url", "archiveId":"archive_id", "courseCode":"course_code",
                       "dateModified": "modified_date", "modifierId":"modifier_id", "courseId":"course_id",
                       "description":"description", "inLanguage":"language_id", "creditPoints":"credit_points",
                       "teacherId":"teacher_id", "teacherName":"teacher_name"}
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
