# coding=UTF-8
#
# Provides the database API to access and modify persistent data
# in the Exam Archive.
#
# @authors: Ari Kairala, Petteri Ponsimaa
# The class is based on code made by Ivan Sanchez (from exercise 4 code of resources.py).


import json, os
import course_resource

from flask import Flask, request, Response, g, jsonify, send_from_directory
from flask.ext.restful import Resource, Api, abort
from werkzeug import secure_filename

from exam_archive import ExamDatabaseErrorExists
from resources_common import auth, app, api, error_response, API_VERSION, COLLECTIONJSON, EXAM_PROFILE, \
    allowed_file, file_extension, DEFAULTJSON

# Define the resources
class ExamList(Resource):
    '''
    Resource ExamList implementation
    '''
    
    @auth.login_required
    def get(self, archive_id, course_id):
        '''
        Get a list of exams in the exam archive.

        INPUT:

        * `archive_id`: Identifier of the archive in which the exam belongs to
        * `course_id`: Identifier of the course, in which the exam belongs to

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.

        ENTITY BODY OUTPUT FORMAT:

        * `Media type`: Collection+JSON:
            http://amundsen.com/media-types/collection/

        * `Profile`: Exam profile
            http://atlassian.virtues.fi:8090/display/PWP/PWP11#Exam+profile

        RETURN CODES:

        `200` A list of exams was fetched and returned successfully.
        `400` No archive id. The archive id was not specified.
        `400` No course id. The course id was not specified.
        `401` Not logged in. You are not logged in, unable to get exam list information.
        `403` Access forbidden. You are not authorizated to access the exam list.
        `404` Course not found. The course was not found.

        In case of error, the response media type Problem+JSON is returned with the error message above. If there are
        no exams in the course, a collection with empty items container is returned.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable to get exam list information")
        if not g.user_logged_in or (g.user_type in ['basic','admin'] and g.user_archive != archive_id):
            return error_response(403, "Access forbidden", "You are not authorizated to access the exam list")

        if not archive_id:
            return error_response(400, "No archive id", "The archive id was not specified")
        if not course_id:
            return error_response(400, "No course id", "The course id was not specified")

        # Get course from the database
        course = g.db.get_course(course_id)
        if not course:
            return error_response(404, "Course not found", "The course was not found")

        # Extract exams from the database
        exams = g.db.browse_exams(course_id)

        # FILTER AND GENERATE RESPONSE

        # Create the envelope
        envelope = {}
        collection = {}
        collection_links = []
        envelope["collection"] = collection
        collection['version'] = API_VERSION
        collection['href'] = api.url_for(ExamList, archive_id=archive_id, course_id=course_id)
        collection['links'] = collection_links

        collection_links.append({'name':"parent_course",
                                 'prompt':'Course %s' % course['course_name'],
                                 'rel':'course','href': api.url_for(course_resource.Course, archive_id=archive_id,
                                                                    course_id=course_id)})

        collection_links.append({'name':"course_list",
                                 'prompt':'Course list',
                                 'rel':'courses','href': api.url_for(course_resource.CourseList, archive_id=archive_id)})

        collection['template'] = {
            "data" : [
                {"prompt" : "Insert examiner ID", "name" : "examinerId", "value" : "", "required":False},
                {"prompt" : "Insert exam date (YYYY-MM-DD)", "name" : "date", "value" : "", "required":False},
                {"prompt" : "Insert exam file attachment", "name" : "associatedMedia", "value" : "", "required":False},
                {"prompt" : "Insert exam language ID", "name" : "inLanguage", "value" : "", "required":False}
            ]
        }

        # Create the items
        items = []
        for exam in exams:
            # Get the needed attributes from the exam object
            exam_id = exam['exam_id']
            course_id = exam['course_id']
            date = exam['date']
            file_attachment = exam['file_attachment']
            lang = exam['language_id']

            # Get some course properties for forming a proper link resource URL
            course_name = course['course_name']
            course_code = course['course_code']

            item = {}
            data = []
            links = []
            item['href'] = api.url_for(Exam, archive_id=archive_id, course_id=course_id, exam_id=exam_id)
            item['read-only'] = True
            item['data'] = data
            item['links'] = links

            # Append proper fields with values to items
            data.append({'name':'examId', 'value':exam_id})
            data.append({'name':'courseId', 'value':course_id})
            data.append({'name':'date', 'value':date})
            data.append({'name':'associatedMedia', 'value':file_attachment})
            data.append({'name':'inLanguage', 'value':lang})
            data.append({'name':'dateModified', 'value':exam['last_modified']})

            examiner_id = exam['examiner_id']
            if examiner_id:
                teacher = g.db.get_teacher(examiner_id)
                teacher_name = "%s %s" % (teacher['first_name'], teacher['last_name'])
                data.append({'name':'examinerId', 'value':examiner_id})
                data.append({'name':'examinerName', 'value':teacher_name})

            modifier_id = exam['modifier_id']
            if modifier_id:
                modifier = g.db.get_user(modifier_id)
                modifier_name = modifier['username']
                data.append({'name':'modifier', 'value':modifier_name})

            link = {'name':"%s_exams" % course_code, 'prompt':'Other exams of the course %s' % course_name,
                       'rel':'exams','href': api.url_for(ExamList, archive_id=archive_id, course_id=course_id)}
            links.append(link)

            items.append(item)

        collection['items'] = items

        # Return the response with status code 200 and Collection+JSON mime type and URL to Course profile
        return Response (json.dumps(envelope), 200, mimetype=COLLECTIONJSON+";"+EXAM_PROFILE)

    
    @auth.login_required
    def post(self, archive_id, course_id):
        '''
        Adds a new exam to the exam archive. Authorization is required (user must be of type 'super').

        INPUT:

        * `archive_id` : Identifies the archive, where an course belongs to
        * `course_id` : Identifies the course, where the exam belongs to

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.

        ENTITY BODY OUTPUT FORMAT:

        * `Media type`: Collection+JSON:
            http://amundsen.com/media-types/collection/

        * `Profile`: Exam profile
            http://atlassian.virtues.fi:8090/display/PWP/PWP11#Exam+profile

        RETURN CODES:

        `201` New exam was added successfully.
        `400` No archive id. The archive id was not specified.
        `400` No course id The course id was not specified.
        `400` User type was incorrectly none of the following: basic, admin or super.
        `400` Error in request format. Request format does not follow the template.
        `400` Error in request format. Date is required.
        `400` Error in request format. Date must be in format YYYY-MM-DD.
        `401` Not logged in. You are not logged in, unable to add new exam.
        `403` Access forbidden. You are not authorizated. (must be a user of type 'super')
        `404` Course not found. The course was not found.
        `409` Error adding new exam. Another exam already exists within the same course, with same date and language.
        `415` Unsupported media type. Use a JSON compatible format.
        `500` Database error. Please, contact the administrator.

        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable to add new exam")
        if not g.user_logged_in or not g.user_type in ['admin','super'] or (g.user_type == 'admin' and g.user_archive != archive_id):
            return error_response(403, "Access forbidden", "You are not authorizated")

        # Convert the request body to JSON. If it fails get_json method throws an exception. Catch it and report it to
        # the user as an error. Set silent = True to let us replace '400 bad request' with more detailed error message.
        input = request.get_json(force=True, silent=True)

        if not input:
            return error_response(415, "Unsupported media type", "Use a JSON compatible format")

        if not archive_id:
            return error_response(400, "No archive id", "The archive id was not specified")
        if not course_id:
            return error_response(400, "No course id", "The course id was not specified")

        # Get course from the database
        course = g.db.get_course(course_id)
        if not course:
            return error_response(404, "Course not found", "The course was not found")

        # Get the date from template. If the template is malformed, catch the exception and report an error.
        try:
            data = input['template']['data']
            print 'ok'
            # The only required attributes are name and archiveId
            date = None
            examiner_id = None
            file_attachment = None
            language_id = 'fi'
            modifier_id = g.user_logged_in

            for d in data:
                if d['name'] == 'date':
                    date = d['value']
                elif d['name'] == 'examinerId':
                    examiner_id = d['value']
                elif d['name'] == 'associatedMedia':
                    file_attachment = d['value']
                elif d['name'] == 'inLanguage':
                    language_id = d['value']
        except:
            #This is launched if either title or body does not exist or if
            # the template.data array does not exist.
            return error_response(400, "Error in request format", "Request format does not follow the template")

        # Check the date is valid
        if not date:
            return error_response(400, "Error in request format", "Date is required")

        # Try to create the new exam
        try:
            new_exam_id = g.db.create_exam(course_id, examiner_id, date, file_attachment, language_id, modifier_id)

        except ExamDatabaseErrorExists as e:
            return error_response(409, "Error adding new exam", "Another exam already exists within the same course, with same date and language")
        except ValueError:
            return error_response(400, "Error in request format", 'Date must be in format YYYY-MM-DD')

        if not new_exam_id:
            return error_response(500, "Database error", "Please, contact the administrator")

        # Create the location header with the examname of the newly added exam
        url = api.url_for(Exam, archive_id=archive_id, course_id=course_id, exam_id=new_exam_id)

        # Return the response with status code 201 and location header with URL pointing to new resource
        return Response(status=201, headers={'Location':url}, mimetype=DEFAULTJSON)

# Define the resources
class Exam(Resource):
    '''
    Resource Exam implementation
    '''
    
    @auth.login_required
    def get(self, archive_id, course_id, exam_id):
        '''
        Get a list of exams in the exam archive.

        INPUT:

        * `archive_id` : Identifies the archive, where an course belongs to
        * `course_id` : Identifies the course, where the exam belongs to
        * `exam_id`: Identifier of the exam

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.

        ENTITY BODY OUTPUT FORMAT:

        * `Media type`: Collection+JSON:
            http://amundsen.com/media-types/collection/

        * `Profile`: Exam profile
            http://atlassian.virtues.fi:8090/display/PWP/PWP11#Exam+profile

        RETURN CODES:

        `200` Exam information was returned succesfully.
        `400` No archive id. The archive id was not specified.
        `400` No course id. The course id was not specified.
        `400` No exam id. The exam id was not specified.
        `401` Not logged in. You are not logged in, unable to get exam list information.
        `403` Access forbidden. You are not authorizated to access the exam list.
        `404` Course not found. The course was not found.
        `404` Not found. Given exam not found.

        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable to get exam list information")
        if not g.user_logged_in or (g.user_type in ['basic','admin'] and g.user_archive != archive_id):
            return error_response(403, "Access forbidden", "You are not authorizated to access the exam list")

        if not archive_id:
            return error_response(400, "No archive id", "The archive id was not specified")
        if not course_id:
            return error_response(400, "No course id", "The course id was not specified")
        if not exam_id:
            return error_response(400, "No exam id", "The exam id was not specified")

        # Get course from the database
        course = g.db.get_course(course_id)
        if not course:
            return error_response(404, "Course not found", "The course was not found")

        # Extract exams from the database
        exam = g.db.get_exam(exam_id)

        if not exam:
            return error_response(404, "Not found", "Given exam not found")

        # Create the envelope
        envelope = {}
        collection = {}
        collection_links = []
        envelope["collection"] = collection
        collection['version'] = API_VERSION
        collection['href'] = api.url_for(Exam, archive_id=archive_id, course_id=course_id, exam_id=exam_id)
        collection['links'] = collection_links

        collection_links.append({'name':"parent_course",
                                 'prompt':'Course %s' % course['course_name'],
                                 'rel':'course','href': api.url_for(course_resource.Course, archive_id=archive_id,
                                                                    course_id=course_id)})

        collection_links.append({'name':"exam_list",
                                 'prompt':'List of all exams in the course %s' % course['course_name'],
                                 'rel':'exams','href': api.url_for(ExamList, archive_id=archive_id, course_id=course_id)})

        collection['template'] = {
            "data" : [
                {"prompt" : "Insert examiner ID", "name" : "examinerId", "value" : "", "required":False},
                {"prompt" : "Insert exam date (YYYY-MM-DD)", "name" : "date", "value" : "", "required":False},
                {"prompt" : "Insert exam file attachment", "name" : "associatedMedia", "value" : "", "required":False},
                {"prompt" : "Insert exam language ID", "name" : "inLanguage", "value" : "", "required":False}
            ]
        }

        # Create the items
        items = []

        # Get the needed attributes from the exam object
        exam_id = exam['exam_id']
        course_id = exam['course_id']
        date = exam['date']
        file_attachment = exam['file_attachment']
        lang = exam['language_id']

        # Get some course properties for forming a proper link resource URL
        course_name = course['course_name']
        course_code = course['course_code']

        item = {}
        data = []
        links = []
        item['href'] = api.url_for(Exam, archive_id=archive_id, course_id=course_id, exam_id=exam_id)
        item['read-only'] = True
        item['data'] = data
        item['links'] = links

        data.append({'name':'courseId', 'value':course_id})
        data.append({'name':'examId', 'value':exam_id})
        data.append({'name':'date', 'value':date})
        data.append({'name':'associatedMedia', 'value':file_attachment})
        data.append({'name':'inLanguage', 'value':lang})
        data.append({'name':'dateModified', 'value':exam['last_modified']})

        examiner_id = exam['examiner_id']
        if examiner_id:
            teacher = g.db.get_teacher(examiner_id)
            teacher_name = "%s %s" % (teacher['first_name'], teacher['last_name'])
            data.append({'name':'examinerId', 'value':examiner_id})
            data.append({'name':'examinerName', 'value':teacher_name})

        modifier_id = exam['modifier_id']
        if modifier_id:
            modifier = g.db.get_user(modifier_id)
            modifier_name = modifier['username']
            data.append({'name':'modifier', 'value':modifier_name})

        link = {'name':"%s_exams" % course_code, 'prompt':'Other exams of the course %s' % course_name,
                   'rel':'exams','href': api.url_for(ExamList, archive_id=archive_id, course_id=course_id)}
        links.append(link)

        items.append(item)

        collection['items'] = items

        # Return the response with status code 200 and Collection+JSON mime type and URL to Course profile
        return Response (json.dumps(envelope), 200, mimetype=COLLECTIONJSON+";"+EXAM_PROFILE)

    
    @auth.login_required
    def put(self, archive_id, course_id, exam_id):
        '''
        Modify an existing exam. Authorization is required (user must be of type 'admin' or 'super').

        INPUT:

        * `archive_id` : Identifies the archive, where an course belongs to
        * `course_id` : Identifies the course, where the exam belongs to
        * `exam_id` : Identifies the exam, that is going to be updated

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.

        ENTITY BODY OUT FORMAT:

        * `Media type`: Collection+JSON:
            http://amundsen.com/media-types/collection/

        * `Profile`: Exam profile
            http://atlassian.virtues.fi:8090/display/PWP/PWP11#Exam+profile

        RETURN CODES:

        `200` New exam was added successfully.
        `400` No archive id. The archive id was not specified.
        `400` No course id. The course id was not specified.
        `400` No exam id. The exam id was not specified.
        `400` Error in request format. Request format does not follow the template.
        `400` Error in request format. Date must be in format YYYY-MM-DD.
        `401` Not logged in. You are not logged in, unable to add new exam.
        `403` Access forbidden. You are not authorizated. (must be a user of type 'super')
        `404` Course not found. The course was not found.
        `404` Exam not found. The exam was not found.
        `409` Error adding new exam. Another exam already exists within the same course, with same date and language.
        `415` Unsupported media type. Use a JSON compatible format.
        `500` Database error. Please, contact the administrator.

        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable to add new exam")
        if not g.user_logged_in or not g.user_type in ['admin','super'] or (g.user_type == 'admin' and g.user_archive != archive_id):
            return error_response(403, "Access forbidden", "You are not authorizated")

        # Convert the request body to JSON. If it fails get_json method throws an exception. Catch it and report it to
        # the user as an error. Set silent = True to let us replace '400 bad request' with more detailed error message.
        input = request.get_json(force=True, silent=True)

        if not input:
            return error_response(415, "Unsupported media type", "Use a JSON compatible format")

        if not archive_id:
            return error_response(400, "No archive id", "The archive id was not specified")
        if not course_id:
            return error_response(400, "No course id", "The course id was not specified")
        if not exam_id:
            return error_response(400, "No exam id", "The exam id was not specified")

        # Get the given course from the database
        course = g.db.get_course(course_id)
        if not course:
            return error_response(404, "Course not found", "The course was not found")

        # Get the given exam from the database
        exam = g.db.get_exam(exam_id)
        if not course:
            return error_response(404, "Exam not found", "The exam was not found")

        # Get the date from template. If the template is malformed, catch the exception and report an error.
        try:
            data = input['template']['data']

            # The only required attributes are name and archiveId
            date = exam['date']
            examiner_id = exam['examiner_id']
            file_attachment = exam['file_attachment']
            language_id = exam['language_id']
            modifier_id = g.user_logged_in

            for d in data:
                if d['name'] == 'date':
                    date = d['value']
                elif d['name'] == 'examinerId':
                    examiner_id = d['value']
                elif d['name'] == 'associatedMedia':
                    file_attachment = d['value']
                elif d['name'] == 'inLanguage':
                    language_id = d['value']
        except:
            #This is launched if either title or body does not exist or if
            # the template.data array does not exist.
            return error_response(400, "Error in request format", "Request format does not follow the template")

        # Try to create the new exam
        try:
            new_exam_id = g.db.edit_exam(exam_id, course_id, examiner_id, date, file_attachment, language_id, modifier_id)

        except ExamDatabaseErrorExists as e:
            return error_response(409, "Error adding new exam", "Another exam already exists within the same course, with same date and language")
        except ValueError:
            return error_response(400, "Error in request format", 'Date must be in format YYYY-MM-DD')

        if not new_exam_id:
            return error_response(500, "Database error", "Please, contact the administrator")

        # Create the location header with the examname of the newly added exam
        url = api.url_for(Exam, archive_id=archive_id, course_id=course_id, exam_id=new_exam_id)

        # Return the response with status code 200 and location header with URL pointing to new resource
        return Response(status=200, headers={'Location':url}, mimetype=DEFAULTJSON)

    
    @auth.login_required
    def delete(self, archive_id, course_id, exam_id):
        '''
        Delete a user from the exam archive. Authorization is required (user must be of type 'super').

        INPUT:

        * `archive_id` : Identifies the archive, where an course belongs to
        * `course_id` : Identifies the course, where the exam belongs to
        * `exam_id` : Identifies the exam, that is going to be deleted

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.

        RETURN CODES:

        `204` Exam entity successfully deleted.
        `401` Not logged in. You are not logged in, unable delete the user.
        `403` Access forbidden. You are not authorizated. (must be a user of type 'super')
        `404` Exam not found. Given exam was not found.
        `500` Database error. Please, contact the adminnistrator.

        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable delete the user")
        if not g.user_logged_in or not g.user_type in ['admin','super'] or (g.user_type == 'admin' and g.user_archive != archive_id):
            return error_response(403, "Access forbidden", "You are not authorizated")

        # Extract users from the database
        exam = g.db.get_exam(exam_id)

        if not exam:
            return error_response(404, "Exam not found", "Given exam was not found")

        # Try to delete the exam
        success = g.db.remove_exam(exam_id)

        if not success:
            return error_response(500, "Database error", "Please, contact the adminnistrator")

        #Return the response
        return Response(status=204, mimetype=DEFAULTJSON)

# Define the resources
class ExamUpload(Resource):
    '''
    Resource ExamUpload implementation.

    Note: The code is adapted from an example by Petrus Jvrensburg (2013):
    http://stackoverflow.com/questions/15040706/streaming-file-upload-using-bottle-or-flask-or-similar
    '''

    @auth.login_required
    def get(self, archive_id, course_id, exam_id):
        '''
        Check if the actual exam attachment has been uploaded.

        INPUT:

        * `archive_id` : Identifies the archive, where an course belongs to
        * `course_id` : Identifies the course, where the exam belongs to
        * `exam_id` : Identifies the exam, that is going to be checked

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.

        RETURN CODES:

        `200` Exam attachment found.
        `404` Exam not found. Given exam was not found.
        `500` Database error. Please, contact the adminnistrator.

        If the exam was found, an URL is returned in 'Location' header, where to download the exam.
        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''

        # Extract exam from the database
        course = g.db.get_course(course_id)

        if not course:
            return error_response(404, "Course not found", "Given course was not found")

        # Extract exam from the database
        exam = g.db.get_exam(exam_id)

        if not exam or not exam['file_attachment']:
            return error_response(404, "Exam not found", "Given exam was not found")
        else:
            return Response(200, mimetype=DEFAULTJSON, headers={'Location':exam['file_attachment']})

    
    @auth.login_required
    def post(self, archive_id, course_id, exam_id):
        '''
        Upload the exam attachment.

        INPUT:

        * `archive_id` : Identifies the archive, where an course belongs to
        * `course_id` : Identifies the course, where the exam belongs to
        * `exam_id` : Identifies the exam, that is going to be deleted

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.
        * `files`: The file attachment to be uploaded

        RETURN CODES:

        `201` Exam attachment has been successfully uploaded.
        `400` Upload error. Actual file was not included in the request.
        `400` Upload error. Invalid file name. Only allowed extensions are txt, pdf, png, jpg, jpeg and gif.
        `404` Exam not found. Given exam was not found.
        `500` Database error. Please, contact the adminnistrator.

        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''

        # Extract exam from the database
        course = g.db.get_course(course_id)

        if not course:
            return error_response(404, "Course not found", "Given course was not found")

        # Extract exam from the database
        exam = g.db.get_exam(exam_id)

        if not exam:
            return error_response(404, "Exam not found", "Given exam was not found")

        # Get the files from request
        files = request.files
        upload_folder = app.static_folder  # os.path.join("api", app.config['UPLOAD_FOLDER'])
        modifier_id = g.user_logged_in

        # Assuming that only one file is passed in the request
        if len(files.keys()):
            key = files.keys()[0]
            file = files[key]              # this is a Werkzeug FileStorage object
            filename = file.filename
        else:
            return error_response(400, "Upload error", "Actual file was not included in the request")

        if allowed_file(filename):
            filename = "%s_%s.%s" % (course['course_code'], exam['date'], file_extension(filename))
            pathname = os.path.join(upload_folder, secure_filename(filename))
            resource_path = "%s/%s" % (app.config['UPLOAD_FOLDER'], secure_filename(filename))
        else:
            return error_response(400, "Upload error", "Invalid file name. Only allowed extensions are txt, pdf, png, jpg, jpeg and gif")

        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        if 'Content-Range' in request.headers:
            # Extract starting byte from Content-Range header string
            range_str = request.headers['Content-Range']
            start_bytes = int(range_str.split(' ')[1].split('-')[0])

            # append chunk to the file on disk, or create new
            with open(pathname, 'a') as f:
                f.seek(start_bytes)
                f.write(file.stream.read())

        else:
            # This is not a chunked request, so just save the whole file
            file.save(pathname)

        # Update to filename to database
        try:
            success = g.db.edit_exam_file(exam_id, resource_path, modifier_id)
        except Exception as e:
            return error_response(500, "Database error", e.message)

        if not success:
            return error_response(500, "Database error", "Please, contact the administrator")

        # send response with appropriate mime type header
        return Response(status=201, headers={'Location':resource_path, 'size': os.path.getsize(pathname)},
                        mimetype=DEFAULTJSON)
