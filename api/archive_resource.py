# coding=UTF-8
#
# Provides the database API to access and modify persistent data
# in the Exam Archive.
#
# @authors: Ari Kairala, Petteri Ponsimaa
# The class is based on code made by Ivan Sanchez (from exercise 4 code of resources.py).


import json
import course_resource

from flask import Flask, request, Response, g, jsonify
from flask.ext.restful import Resource, Api, abort

from exam_archive import ExamDatabaseError, ExamDatabaseErrorExists
from resources_common import auth, app, api, error_response, API_VERSION, COLLECTIONJSON, ARCHIVE_PROFILE, \
    DEFAULTJSON, EXAM_ARCHIVE

# Define the resources
class ArchiveList(Resource):
    '''
    Resource ArchiveList implementation
    '''
    
    @auth.login_required
    def get(self):
        '''
        Get a list of archives in the exam archive.

        INPUT:

        * `None`

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.

        ENTITY BODY OUTPUT FORMAT:

        * `Media type`: Collection+JSON:
            http://amundsen.com/media-types/collection/

        * `Profile`: Archive profile
            http://atlassian.virtues.fi:8090/display/PWP/PWP11#PWP11-Archiveprofile

        RETURN CODES:

        `200` A list of archives in database was returned succesfully.
        `401` Not logged in. You are not logged in, unable to get archive information.

        In case of error, the response media type Problem+JSON is returned with the error message above. If there are
        no archives in the database, a collection with empty items container is returned.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable to get archive information")
        if not g.user_logged_in:
            return error_response(403, "Access forbidden", "You are not authorizated to access the archive information")

        # Extract archives from the database
        archives = g.db.browse_archives()

        # FILTER AND GENERATE RESPONSE

        # Create the envelope
        envelope = {}
        collection = {}
        envelope["collection"] = collection
        collection['version'] = API_VERSION
        collection['href'] = api.url_for(ArchiveList)

        collection['template'] = {
            "data" : [
                {"prompt" : "Archive ID", "name" : "archiveId", "value" : "", "required":False},
                {"prompt" : "Archive name", "name" : "name", "value" : "", "required":True},
                {"prompt" : "Organisation name", "name" : "organisationName", "value" : "", "required":True},
                {"prompt" : "Whether authorization is required from basic users to view exams",
                 "name" : "identificationNeeded", "value" : "", "required":True}
            ]
        }

        # Create the items
        items = []
        for archive in archives:
            archive_name = archive['archive_name']
            archive_id = archive['archive_id']
            organisation_name = archive['organisation_name']
            identification_needed = archive['identification_needed']

            if g.user_type == 'super' or (g.user_type in ['basic','admin'] and g.user_archive == archive_id):

                item = {}
                data = []
                links = []
                item['href'] = api.url_for(Archive, archive=archive_id)
                item['read-only'] = True
                item['data'] = data
                item['links'] = links

                # Append proper fields with values to items
                data.append({'name':'archiveId', 'value':archive_id})
                data.append({'name':'name', 'value':archive_name})
                data.append({'name':'organisationName', 'value':organisation_name})
                data.append({'name':'identificationNeeded', 'value':identification_needed})
                data.append({'name':'dateModified', 'value':archive['last_modified']})

                modifier_id = archive['modifier_id']
                if modifier_id:
                    modifier = g.db.get_user(modifier_id)
                    modifier_name = modifier['username']
                    data.append({'name':'modifier', 'value':modifier_name})

                courses = g.db.browse_courses(archive_id)
                if courses:
                    link = {'name':"course_list",
                            'prompt':'Courses of archive %s' % archive_name,
                            'rel':'courses','href': api.url_for(course_resource.CourseList, archive_id=archive_id)}
                    links.append(link)

                items.append(item)

        collection['items'] = items

        # Return the response with status code 200 and Collection+JSON mime type and URL to Archive profile
        return Response (json.dumps(envelope), 200, mimetype=COLLECTIONJSON+";"+ARCHIVE_PROFILE)

    @auth.login_required
    def post(self):
        '''
        Adds a new archive to the exam archive. Authorization is required (user must be of type 'super').

        INPUT:

        * `None`

        HEADERS:

        * `Accept` : application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.

        ENTITY BODY INPUT FORMAT:
        * Media type: Collection+JSON
        * Profile: Archive_profile

        * Media type: Collection+JSON:
            http://amundsen.com/media-types/collection/

        * Profile: Archive profile
            http://atlassian.virtues.fi:8090/display/PWP/PWP11#Archive+profile

        The body should be a Collection+JSON template. Semantic descriptors used in template are name, userType,
        accessCode and archiveId.

        RETURN CODES:

        `201` New archive was added successfully.
        `400` Error in request format. Request format does not follow the template.
        `400` Error in request format. Archive name is required.
        `401` Not logged in. You are not logged in, unable to add new archive.
        `403` Access forbidden. You are not authorizated.
        `404` Modifier not found. Given mofifier id was not found.
        `409` Error adding new archive. Archive with the same archive and organisation name already exists.
        `415` Unsupported media type. Use a JSON compatible format.
        `500` Database error. Please, contact the administrator.

        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable to add new archive")
        if not g.user_logged_in or not g.user_type in ['super','admin']:
            return error_response(403, "Access forbidden", "You are not authorizated")

        # Convert the request body to JSON. If it fails get_json method throws an exception. Catch it and report it to
        # the user as an error. Set silent = True to let us replace '400 bad request' with more detailed error message.
        input = request.get_json(force=True, silent=True)

        if not input:
            return error_response(415, "Unsupported media type", "Use a JSON compatible format")

        # Get the date from template. If the template is malformed, catch the exception and report an error.
        try:
            data = input['template']['data']

            # The required attributes are archive and organisation name
            archive_name = None
            organisation_name = None
            identification_needed = False
            modifier_id = g.user_logged_in

            for d in data:
                if d['name'] == 'name':
                    archive_name = d['value']
                elif d['name'] == 'organisationName':
                    organisation_name = d['value']
                elif d['name'] == 'identificationNeeded':
                    identification_needed = d['value']

        except:
            #This is launched if either title or body does not exist or if
            # the template.data array does not exist.
            return error_response(400, "Error in request format", "Request format does not follow the template")

        # Check the data is valid
        if not archive_name or not organisation_name:
            return error_response(400, "Error in request format", "Archive and organisation name are required")

        # Try to create the new archive
        try:
            new_archive_id = g.db.create_archive(archive_name, organisation_name, identification_needed, modifier_id)

        except ExamDatabaseErrorExists:
            return error_response(409, "Error adding new archive",
                                  "Archive with the same archive and organisation name already exists")
        except ExamDatabaseErrorNotFound:
            return error_response(404, "Modifier not found",
                                  "Given mofifier id was not found")

        if not new_archive_id:
            return error_response(500, "Database error", "Please, contact the administrator")

        # Create the location header with the archivename of the newly added archive
        url = api.url_for(Archive, archive=new_archive_id)

        # Return the response with status code 201 and location header with URL pointing to new resource
        return Response(status=201, headers={'Location':url}, mimetype=DEFAULTJSON)

# Define the resources
class Archive(Resource):
    '''
    Resource Archive implementation
    '''
    
    @auth.login_required
    def get(self, archive):
        '''
        Get details of an archive.

        INPUT:

        * `archive`: Identifier of the archive.

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.

        ENTITY BODY OUTPUT FORMAT:

        * `Media type`: Collection+JSON:
            http://amundsen.com/media-types/collection/

        * `Profile`: Archive profile
            http://atlassian.virtues.fi:8090/display/PWP/PWP11#PWP11-Archiveprofile

        RETURN CODES:

        `200` Archive information was returned succesfully.
        `401` Not logged in. You are not logged in, unable to get archive information.
        `404` Not found. Archive not found.

        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable to get archive information")
        if not g.user_logged_in or (g.user_type in ['basic','admin'] and g.user_archive != archive):
            return error_response(403, "Access forbidden", "You are not authorizated to access the archive information")

        # Extract the archive from the database
        archive = g.db.get_archive(archive)

        if not archive:
            return error_response(404, "Not found", "Archive not found")

        # FILTER AND GENERATE RESPONSE

        # Create the envelope
        envelope = {}
        collection = {}
        collection_links = []
        envelope["collection"] = collection
        collection['version'] = API_VERSION
        collection['href'] = api.url_for(Archive, archive=archive['archive_id'])
        collection['links'] = collection_links

        collection_links.append({'name':"archive_list",
                                 'prompt':'Archive list',
                                 'rel':'archives','href': api.url_for(ArchiveList)})

        collection['template'] = {
            "data" : [
                {"prompt" : "Archive ID", "name" : "archiveId", "value" : "", "required":False},
                {"prompt" : "Archive name", "name" : "name", "value" : "", "required":True},
                {"prompt" : "Organisation name", "name" : "organisationName", "value" : "", "required":True},
                {"prompt" : "Whether authorization is required from basic users to view exams",
                 "name" : "identificationNeeded", "value" : "", "required":True}
            ]
        }

        # Create the items
        items = []

        archive_name = archive['archive_name']
        archive_id = archive['archive_id']
        organisation_name = archive['organisation_name']
        identification_needed = archive['identification_needed']

        item = {}
        data = []
        links = []
        item['href'] = api.url_for(Archive, archive=archive_id)
        item['read-only'] = True
        item['data'] = data
        item['links'] = links

        # Append proper fields with values to items
        data.append({'name':'archiveId', 'value':archive_id})
        data.append({'name':'name', 'value':archive_name})
        data.append({'name':'organisationName', 'value':organisation_name})
        data.append({'name':'identificationNeeded', 'value':identification_needed})
        data.append({'name':'dateModified', 'value':archive['last_modified']})

        modifier_id = archive['modifier_id']
        if modifier_id:
            modifier = g.db.get_user(modifier_id)
            modifier_name = modifier['username']
            data.append({'name':'modifier', 'value':modifier_name})

        link = {'name':"course_list",
                'prompt':'Courses of archive %s' % archive_name,
                   'rel':'courses','href': api.url_for(course_resource.CourseList, archive_id=archive_id)}
        links.append(link)

        items.append(item)

        collection['items'] = items

        # Return the response with status code 200 and Collection+JSON mime type and URL to Archive profile
        return Response (json.dumps(envelope), 200, mimetype=DEFAULTJSON)

    @auth.login_required
    def put(self, archive):
        '''
        Update a archive in the exam archive. Authorization is required (user must be of type 'super').

        INPUT:

        * `archive_id` Identifies the archive to be updated

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.

        ENTITY BODY OUTPUT FORMAT:

        * `Media type`: Collection+JSON:
            http://amundsen.com/media-types/collection/

        * `Profile`: Archive profile
            http://atlassian.virtues.fi:8090/display/PWP/PWP11#Archive+profile

        RETURN CODES:

        `200` New archive was added successfully.
        `400` Error in request format. Request format does not follow the template.
        `400` Error in request format. Archive name is required.
        `401` Not logged in. You are not logged in, unable to add new archive.
        `403` Access forbidden. You are not authorizated.
        `404` Archive not found. Given archive id was not found.
        `404` Modifier not found. Given mofifier id was not found.
        `409` Error updating archive. Archive with the same archive and organisation name already exists.
        `415` Unsupported media type: Use a JSON compatible format.
        `500` Database error. Please, contact the administrator.

        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable to add new archive")
        if not g.user_logged_in or not g.user_type in ['super','admin'] or \
                (g.user_type == 'admin' and g.user_archive != archive):
            return error_response(403, "Access forbidden", "You are not authorizated")

        # Extract archive from the database
        archive = g.db.get_archive(archive)

        if not archive:
            return error_response(404, "Archive not found", "Given archive id was not found")

        # Convert the request body to JSON. If it fails get_json method throws an exception. Catch it and report it to
        # the user as an error. Set silent = True to let us replace '400 bad request' with more detailed error message.
        input = request.get_json(force=True, silent=True)

        if not input:
            return error_response(415, "Unsupported media type", "Use a JSON compatible format")

        try:
            # Get the data from template. If the template is malformed, catch the exception and report an error.
            data = input['template']['data']

            # The only required attributes are name and archiveId
            archive_id = archive['archive_id']
            archive_name = archive['archive_name']
            organisation_name = archive['organisation_name']
            identification_needed = archive['identification_needed']
            modifier_id = g.user_logged_in

            for d in data:
                if d['name'] == 'name':
                    archive_name = d['value']
                elif d['name'] == 'organisationName':
                    organisation_name = d['value']
                elif d['name'] == 'identificationNeeded':
                    identification_needed = d['value']
                elif d['name'] == 'archiveId' and int(d['value']) != archive_id:
                    return error_response(400, "Error in request format", "It is not allowed to change archive id after creation")
        except:
            #This is launched if either title or body does not exist or if
            # the template.data array does not exist.
            return error_response(400, "Error in request format", "Request format does not follow the template")

        # Check the data is valid
        if not archive_name or not organisation_name:
            return error_response(400, "Error in request format", "Archive and organisation name are required")

        # Try to create the new archive
        try:
            success = g.db.edit_archive(archive_id, archive_name, organisation_name, identification_needed, modifier_id)
        except ExamDatabaseErrorExists:
            return error_response(409, "Error adding new archive",
                                  "Archive with the same archive and organisation name already exists")
        except ExamDatabaseErrorNotFound:
            return error_response(404, "Modifier not found",
                                  "Given mofifier id was not found")

        if not success:
            return error_response(500, "Database error", "Please, contact the administrator")

        # Create the location header with the archivename of the newly added archive
        url = api.url_for(Archive, archive=archive_id)

        # Return the response with status code 201 and location header with URL pointing to new resource
        return Response(status=200, headers={'Location':url}, mimetype=DEFAULTJSON)


    @auth.login_required
    def delete(self, archive):
        '''
        Delete an archive from the exam archive. Authorization is required (user must be of type 'super').

        INPUT:

        * `archive` Identifies the archive, which is going to be deleted

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.

        RETURN CODES:

        `204` Archive entity successfully deleted.
        `401` Not logged in. You are not logged in, unable delete the archive.
        `403` Access forbidden. You are not authorizated (must be a user of type 'super')
        `404` Archive not found. Given archive was not found.
        `500` Database error. Please, contact the adminnistrator.

        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable delete the user")
        if not g.user_logged_in or g.user_type != 'super':
            return error_response(403, "Access forbidden", "You are not authorizated")

        # Extract archive from the database
        archive = g.db.get_archive(archive)

        if not archive:
            return error_response(404, "Archive not found", "Given archive was not found")

        # Try to delete the archive
        success = g.db.remove_archive(archive['archive_id'])

        if not success:
            return error_response(500, "Database error", "Please, contact the adminnistrator")

        #Return the response
        return Response(status=204, mimetype=DEFAULTJSON)
