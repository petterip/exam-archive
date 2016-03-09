# coding=UTF-8
#
# Provides the database API to access and modify persistent data
# in the Examrium.
#
# @authors: Ari Kairala, Petteri Ponsimaa
# The class is based on code made by Ivan Sanchez (from exercise 4 code of resources.py).


import json
import archive_resource
import exam_resource

from flask import Flask, request, Response, g, jsonify
from flask.ext.restful import Resource, Api, abort

from exam_archive import ExamDatabaseError, ExamDatabaseErrorExists
from resources_common import auth, app, api, error_response, EXAM_ARCHIVE, API_VERSION, COLLECTIONJSON, \
    COURSE_PROFILE, DEFAULTJSON

# Define the resources
class CourseList(Resource):
    '''
    Resource CourseList implementation
    '''
    
    @auth.login_required
    def get(self, archive_id):
        '''
        Get a list of courses in the exam archive.

        INPUT:

        * `None`

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.

        ENTITY BODY OUTPUT FORMAT:

        * `Media type`: Collection+JSON:
            http://amundsen.com/media-types/collection/

        * `Profile`: Course profile
            http://atlassian.virtues.fi:8090/display/PWP/PWP11#PWP11-Courseprofile

        RETURN CODES:

        `200` A list of courses in database was returned succesfully.
        `400` No archive id. The archive id was not specified.
        `401` Not logged in. You are not logged in, unable to get course list information.
        `403` Access forbidden. You are not authorizated to access the course list.
        `404` Not found. Given archive was not found.

        In case of error, the response media type Problem+JSON is returned with the error message above. If there are
        no courses in the archive, a collection with empty items container is returned.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable to get course list information")
        if not g.user_logged_in or (g.user_type in ['basic','admin'] and g.user_archive != archive_id):
            return error_response(403, "Access forbidden", "You are not authorizated to access the course list")

        if not archive_id:
            return error_response(400, "No archive id", "The archive id was not specified")

        # Extract the archive from the database
        archive = g.db.get_archive(archive_id)

        if not archive:
            return error_response(404, "Not found", "Given archive was not found")

        # Extract courses from the database
        courses = g.db.browse_courses(archive_id)

        # Create the envelope
        envelope = {}
        collection = {}
        collection_links = []
        envelope["collection"] = collection
        collection['version'] = API_VERSION
        collection['href'] = api.url_for(CourseList, archive_id=archive_id)
        collection['links'] = collection_links

        # Add link to the parent archive list
        collection_links.append({'name':"%s" % EXAM_ARCHIVE.lower().replace(' ','_'),
                              'prompt':'Archive list',
                              'rel':'archives','href': api.url_for(archive_resource.ArchiveList)})

        collection_links.append({'name':"parent_archive",
                                 'prompt':'Archive %s' % archive['archive_name'],
                                 'rel':'archive','href': api.url_for(archive_resource.Archive, archive=archive_id)})

        collection['template'] = {
            "data" : [
                {"prompt" : "Insert course code", "name" : "courseCode", "value" : "", "required":False},
                {"prompt" : "Insert course name", "name" : "name", "value" : "", "required":True},
                {"prompt" : "Insert description", "name" : "description", "value" : "", "required":False},
                {"prompt" : "Insert teacher ID", "name" : "teacherId", "value" : "", "required":False},
                {"prompt" : "Insert course url", "name" : "url", "value" : "", "required":False},
                {"prompt" : "Insert course credit points", "name" : "creditPoints", "value" : "", "required":False},
                {"prompt" : "Insert course language id", "name" : "inLanguage", "value" : "", "required":False}
            ]
        }

        # Create the items
        items = []
        for course in courses:
            course_id = course['course_id']
            archive_id = course['archive_id']
            course_code = course['course_code']
            course_name = course['course_name']
            description = course['description']
            teacher_id = course['teacher_id']
            url = course['url']
            credit_points = course['credit_points']
            lang = course['language_id']

            item = {}
            data = []
            links = []
            item['href'] = api.url_for(Course, archive_id=archive_id, course_id=course_id)
            item['read-only'] = True
            item['data'] = data
            item['links'] = links

            # Append proper fields with values to items
            data.append({'name':'courseId', 'value':course_id})
            data.append({'name':'archiveId', 'value':archive_id})
            data.append({'name':'courseCode', 'value':course_code})
            data.append({'name':'name', 'value':course_name})
            data.append({'name':'description', 'value':description})
            data.append({'name':'url', 'value':url})
            data.append({'name':'inLanguage', 'value':lang})
            data.append({'name':'creditPoints', 'value':credit_points})
            data.append({'name':'dateModified', 'value':course['last_modified']})

            teacher_id = course['teacher_id']
            if teacher_id:
                teacher = g.db.get_teacher(teacher_id)
                teacher_name = "%s %s" % (teacher['first_name'], teacher['last_name'])
                data.append({'name':'teacherId', 'value':teacher_id})
                data.append({'name':'teacherName', 'value':teacher_name})

            modifier_id = course['modifier_id']
            if modifier_id:
                modifier = g.db.get_user(modifier_id)
                modifier_name = modifier['username']
                data.append({'name':'modifier', 'value':modifier_name})

            exams = g.db.browse_exams(course_id)
            if exams:
                link = {'name':"exam_list",
                        'prompt':'Exams of the course %s' % course_name,
                        'rel':'exams',
                        'href': api.url_for(exam_resource.ExamList, archive_id=archive_id, course_id=course_id)}

                links.append(link)

            items.append(item)

        collection['items'] = items

        # Return the response with status code 200 and Collection+JSON mime type and URL to Course profile
        return Response (json.dumps(envelope), 200, mimetype=COLLECTIONJSON+";"+COURSE_PROFILE)

    
    @auth.login_required
    def post(self, archive_id):
        '''
        Adds a new course to the exam archive. Authorization is required (user must be of type 'super').

        INPUT:

        * `archive_id` : Identifies the archive, where course belongs to

        HEADERS:

        * `Accept` : application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.

        ENTITY BODY INPUT FORMAT:
        * Media type: Collection+JSON
        * Profile: Course_profile

        * Media type: Collection+JSON:
            http://amundsen.com/media-types/collection/

        * Profile: Course profile
            http://atlassian.virtues.fi:8090/display/PWP/PWP11#Course+profile

        The body should be a Collection+JSON template.
        Semantic descriptors used in template are name, userType, accessCode and archiveId.

        RETURN CODES:

        `201` New course was added successfully.
        `400` Error in request format. Request format does not follow the template.
        `400` Error in request format. Course name is required.
        `400` User type was incorrectly none of the following: basic, admin or super.
        `401` Not logged in. You are not logged in, unable to add new course.
        `403` Access forbidden. You are not authorizated.
        `409` Error adding new course. Course with the same course name and language id already exists.
        `415` Unsupported media type. Use a JSON compatible format.

        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable to add new course")
        if not g.user_logged_in or not g.user_type in ['super','admin'] or \
                (g.user_type == 'admin' and g.user_archive != archive_id):
            return error_response(403, "Access forbidden", "You are not authorizated")

        # Convert the request body to JSON. If it fails get_json method throws an exception. Catch it and report it to
        # the user as an error. Set silent = True to let us replace '400 bad request' with more detailed error message.
        input = request.get_json(force=True, silent=True)

        if not input:
            return error_response(415, "Unsupported media type", "Use a JSON compatible format")

        # Get the data from template. If the template is malformed, catch the exception and report an error.
        try:
            data = input['template']['data']

            # The only required attributes are name and archiveId
            course_name = None
            course_code = None
            description = None
            teacher_id = None
            credit_points = None
            url = ""
            language_id = 'fi'
            modifier_id = g.user_logged_in

            for d in data:
                if d['name'] == 'name':
                    course_name = d['value']
                elif d['name'] == 'description':
                    description = d['value']
                elif d['name'] == 'teacherId':
                    teacher_id = d['value']
                elif d['name'] == 'archiveId':
                    archive_id = d['value']
                elif d['name'] == 'url':
                    url = d['value']
                elif d['name'] == 'creditPoints':
                    credit_points = d['value']
                elif d['name'] == 'inLanguage':
                    language_id = d['value']
                elif d['name'] == 'courseCode':
                    course_code = d['value']
        except:
            #This is launched if either title or body does not exist or if
            # the template.data array does not exist.
            return error_response(400, "Error in request format", "Request format does not follow the template")

        # Check the data is valid
        if not course_name:
            return error_response(400, "Error in request format", "Course name is required")

        # Try to create the new course
        try:
            new_course_id = g.db.create_course(archive_id, course_code, course_name, description, teacher_id, url,
                                               credit_points, language_id, modifier_id)
        except ExamDatabaseErrorExists:
            return error_response(409, "Error adding new course", "Course with the same course name and language id already exists")

        if not new_course_id:
            return error_response(500, "Database error", "Please, contact the administrator")

        # Create the location header with the coursename of the newly added course
        url = api.url_for(Course, archive_id=archive_id, course_id=new_course_id)

        # Return the response with status code 201 and location header with URL pointing to new resource
        return Response(status=201, headers={'Location':url}, mimetype=DEFAULTJSON)

# Define the resources
class Course(Resource):
    '''
    Resource Course implementation
    '''
    
    @auth.login_required
    def get(self, archive_id, course_id):
        '''
        Get a list of courses in the exam archive.

        INPUT:

        * `archive_id` : Identifies the archive, where course belongs to
        * `course_id` : Identifies the course

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.

        ENTITY BODY OUTPUT FORMAT:

        * `Media type`: Collection+JSON:
            http://amundsen.com/media-types/collection/

        * `Profile`: Course profile
            http://atlassian.virtues.fi:8090/display/PWP/PWP11#PWP11-Courseprofile

        RETURN CODES:

        `200` Course information was returned succesfully.
        `400` No archive id. The archive id was not specified.
        `400` No course id. The course id was not specified.
        `401` Not logged in. You are not logged in, unable to get course list information.
        `403` Access forbidden. You are not authorizated to access the course information.
        `404` Not found. No archive/course found.

        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable to get course information")
        if not g.user_logged_in or (g.user_type in ['basic','admin'] and g.user_archive != archive_id):
            return error_response(403, "Access forbidden", "You are not authorizated to access the course information")

        if not archive_id:
            return error_response(400, "No archive id", "The archive id was not specified")

        # Extract the archive from the database
        archive = g.db.get_archive(archive_id)

        if not archive:
            return error_response(404, "Not found", "Archive not found")

        if not course_id:
            return error_response(400, "No course id", "The course id was not specified")

        # Extract courses from the database
        course = g.db.get_course(course_id)

        if not course:
            return error_response(404, "Not found", "No course found")

        # Create the envelope
        envelope = {}
        collection = {}
        collection_links = []
        envelope["collection"] = collection
        collection['version'] = API_VERSION
        collection['href'] = api.url_for(Course, archive_id=archive_id, course_id=course_id)

        collection['links'] = collection_links

        collection_links.append({'name':"parent_archive",
                                 'prompt':'Archive %s' % archive['archive_name'],
                                 'rel':'archive','href': api.url_for(archive_resource.Archive, archive=archive_id)})

        collection_links.append({'name':"course_list",
                                 'prompt':'List of all courses in the archive %s' % archive['archive_name'],
                                 'rel':'courses','href': api.url_for(CourseList, archive_id=archive_id)})

        collection['template'] = {
            "data" : [
                {"prompt" : "Insert course ID", "name" : "courseId", "value" : "", "required":True},
                {"prompt" : "Insert archive ID", "name" : "archiveId", "value" : "", "required":True},
                {"prompt" : "Insert course code", "name" : "courseCode", "value" : "", "required":False},
                {"prompt" : "Insert course name", "name" : "name", "value" : "", "required":True},
                {"prompt" : "Insert description", "name" : "description", "value" : "", "required":False},
                {"prompt" : "Insert teacher ID", "name" : "teacherId", "value" : "", "required":False},
                {"prompt" : "Insert course url", "name" : "url", "value" : "", "required":False},
                {"prompt" : "Insert course credit points", "name" : "creditPoints", "value" : "", "required":False},
                {"prompt" : "Insert course language id", "name" : "inLanguage", "value" : "", "required":False}
            ]
        }

        # Create the items
        items = []

        course_id = course['course_id']
        archive_id = course['archive_id']
        course_code = course['course_code']
        course_name = course['course_name']
        description = course['description']
        url = course['url']
        credit_points = course['credit_points']
        lang = course['language_id']

        item = {}
        data = []
        links = []
        item['href'] = api.url_for(Course, archive_id=archive_id, course_id=course_id)
        item['read-only'] = True
        item['data'] = data
        item['links'] = links

        # Append proper fields with values to items
        data.append({'name':'courseId', 'value':course_id})
        data.append({'name':'archiveId', 'value':archive_id})
        data.append({'name':'courseCode', 'value':course_code})
        data.append({'name':'creditPoints', 'value':credit_points})
        data.append({'name':'name', 'value':course_name})
        data.append({'name':'description', 'value':description})
        data.append({'name':'url', 'value':url})
        data.append({'name':'inLanguage', 'value':lang})
        data.append({'name':'dateModified', 'value':course['last_modified']})

        teacher_id = course['teacher_id']
        if teacher_id:
            teacher = g.db.get_teacher(teacher_id)
            teacher_name = "%s %s" % (teacher['first_name'], teacher['last_name'])
            data.append({'name':'teacherId', 'value':teacher_id})
            data.append({'name':'teacherName', 'value':teacher_name})

        modifier_id = course['modifier_id']
        if modifier_id:
            modifier = g.db.get_user(modifier_id)
            modifier_name = modifier['username']
            data.append({'name':'modifier', 'value':modifier_name})

        link = {'name':"exam_list", 'prompt':'Exams of the course %s' % course_name,
                'rel':'exams','href': api.url_for(exam_resource.ExamList, archive_id=archive_id, course_id=course_id)}
        links.append(link)

        items.append(item)

        collection['items'] = items

        # Return the response with Collection+JSON mime type and URL to Course profile
        return Response (json.dumps(envelope), 200, mimetype=COLLECTIONJSON+";"+COURSE_PROFILE)

    
    @auth.login_required
    def put(self, archive_id, course_id):
        '''
        Update a course in the exam archive. Authorization is required (user must be of type 'super').

        INPUT:

        * `archive_id` : Identifies the archive, where course belongs to
        * `course_id` Identifies the course to be updated

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.

        ENTITY BODY OUTPUT FORMAT:

        * `Media type`: Collection+JSON:
            http://amundsen.com/media-types/collection/

        * `Profile`: Course profile
            http://atlassian.virtues.fi:8090/display/PWP/PWP11#Course+profile

        RETURN CODES:

        `200` New course was added successfully.
        `400` Error in request format. It is not allowed to move a course to a different archive.
        `400` Error in request format. Request format does not follow the template.
        `401` Not logged in. You are not logged in, unable to add new course.
        `403` Access forbidden. You are not authorizated.
        `404` Course not found. Given course id was not found.
        `409` Error updating course. Course with the same course name and language id already exists.
        `415` Unsupported media type: Use a JSON compatible format.
        `500` Database error. Please, contact the administrator.

        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable to add new course")
        if not g.user_logged_in or not g.user_type in ['super','admin'] or \
                (g.user_type == 'admin' and g.user_archive != archive_id):
            return error_response(403, "Access forbidden", "You are not authorizated")

        # Extract course from the database
        course = g.db.get_course(course_id)

        if not course:
            return error_response(404, "Course not found", "Given course id was not found")

        # Convert the request body to JSON. If it fails get_json method throws an exception. Catch it and report it to
        # the user as an error. Set silent = True to let us replace '400 bad request' with more detailed error message.
        input = request.get_json(force=True, silent=True)

        if not input:
            return error_response(415, "Unsupported media type", "Use a JSON compatible format")

        # Get the data from template. If the template is malformed, catch the exception and report an error.
        try:
            data = input['template']['data']

            # The only required attributes are name and archiveId
            archive_id = course['archive_id']
            course_name = course['course_name']
            course_code = course['course_code']
            description = course['description']
            url = course['url']
            teacher_id = course['teacher_id']
            credit_points = course['credit_points']
            language_id = course['language_id']
            modifier_id = g.user_logged_in

            for d in data:
                if d['name'] == 'name':
                    course_name = d['value']
                elif d['name'] == 'description':
                    description = d['value']
                elif d['name'] == 'teacherId':
                    teacher_id = d['value']
                elif d['name'] == 'url':
                    url = d['value']
                elif d['name'] == 'creditPoints':
                    credit_points = d['value']
                elif d['name'] == 'inLanguage':
                    language_id = d['value']
                elif d['name'] == 'courseCode':
                    course_code = d['value']
                elif d['name'] == 'archiveId' and int(d['value']) != archive_id:
                    return error_response(400, "Error in request format", "It is not allowed to move a course to a different archive")

        except:
            #This is launched if either title or body does not exist or if
            # the template.data array does not exist.
            return error_response(400, "Error in request format", "Request format does not follow the template")

        # Try to create the new course
        try:
            success = g.db.edit_course(course_id, course_code, course_name, description, teacher_id, url, credit_points, language_id, modifier_id)
        except ExamDatabaseErrorExists as e:
            return error_response(409, "Error updating course", "Course with the same course name and language id already exists")

        if not success:
            return error_response(500, "Database error", "Please, contact the administrator")

        # Create the location header with the coursename of the newly added course
        url = api.url_for(Course, archive_id=archive_id, course_id=course_id)

        # Return the response with status code 201 and location header with URL pointing to new resource
        return Response(status=200, headers={'Location':url}, mimetype=DEFAULTJSON)

    
    @auth.login_required
    def delete(self, archive_id, course_id):
        '''
        Delete a course from the exam archive. Authorization is required (user must be of type 'super').

        INPUT:

        * `archive_id` : Identifies the archive, where course belongs to
        * `course_id` Identifies the course, which is going to be deleted

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.

        RETURN CODES:

        `204` Course entity successfully deleted.
        `401` Not logged in. You are not logged in, unable delete the course.
        `403` Access forbidden. You are not authorizated (must be a user of type 'super')
        `404` Course not found. Given course was not found.
        `500` Database error. Please, contact the adminnistrator.

        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable delete the user")
        if not g.user_logged_in or not g.user_type in ['super','admin'] or \
                (g.user_type == 'admin' and g.user_archive != archive_id):
            return error_response(403, "Access forbidden", "You are not authorizated")

        # Extract course from the database
        course = g.db.get_course(course_id)

        if not course:
            return error_response(404, "Course not found", "Given course was not found")

        # Try to delete the course
        success = g.db.remove_course(course_id)

        if not success:
            return error_response(500, "Database error", "Please, contact the adminnistrator")

        #Return the response
        return Response(status=204, mimetype=DEFAULTJSON)
