# coding=UTF-8
#
# Provides the database API to access and modify persistent data
# in the Exam Archive.
#
# @authors: Ari Kairala, Petteri Ponsimaa
# The class is based on code made by Ivan Sanchez (from exercise 4 code of resources.py).

import json

from flask import Flask, request, Response, g, jsonify
from flask.ext.restful import Resource, Api, abort
from exam_archive import ExamDatabaseErrorExists
from resources_common import auth, app, api, error_response, API_VERSION, COLLECTIONJSON, USER_PROFILE, DEFAULTJSON
from archive_resource import Archive, ArchiveList

# Define the resources
class UserList(Resource):
    '''
    Resource User implementation
    '''
    
    @auth.login_required
    def get(self):
        '''
        Get a list of users in the exam archive.

        INPUT:

        * `None`

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.
        The User must be admin or super admin.

        ENTITY BODY OUTPUT FORMAT:

        * `Media type`: Collection+JSON:
            http://amundsen.com/media-types/collection/

        * `Profile`: User profile
            http://atlassian.virtues.fi:8090/display/PWP/PWP11#PWP11-Userprofile

        RETURN CODES:

        `200` A list of users having access to the exam archive was fetched and returned successfully.
        `401` Not logged in. You are not logged in, unable to get user information.
        `403` Access forbidden. "You are not authorized to access the user list.
        `404` Not found. No users found.

        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable to get user information")
        if not g.user_logged_in or not g.user_type in ['basic','super','admin']:
            return error_response(403, "Access forbidden", "You are not authorized to access the user list")

        # Extract users from the database
        users = g.db.browse_users()

        if len(users) == 0:
            return error_response(404, "Not found", "No users found")

        # Create the envelope
        envelope = {}
        collection = {}
        envelope["collection"] = collection
        collection['version'] = API_VERSION
        collection['href'] = api.url_for(UserList)

        collection['template'] = {
            "data" : [
                {"prompt" : "Insert user ID", "name" : "userId", "value" : "", "required":False},
                {"prompt" : "Insert user name", "name" : "name", "value" : "", "required":True},
                {"prompt" : "Insert user type", "name" : "userType", "value" : "", "required":False},
                {"prompt" : "Insert user archive", "name" : "archiveId", "value" : "", "required":False},
                {"prompt" : "Insert user password", "name" : "accessCode", "value" : "", "required":True}
            ]
        }

        collection['links'] = [{'name':'user_list', 'prompt':'All the users in the exam archive',
                                'rel':'users','href': api.url_for(UserList)},
                               {'name':'archive_list', 'prompt':'List of accessible archives',
                                'rel':'archives','href': api.url_for(ArchiveList)}]
        # Create the items
        items = []
        for user in users:
            user_id = user['user_id']
            user_type = user['user_type']
            username = user['username']
            password_hash = user['password']

            item = {}
            data = []
            links = []
            item['href'] = api.url_for(User, username=username)
            item['read-only'] = True
            item['data'] = data
            item['links'] = links

            # Add data fields to the item container
            data.append({'name':'userId', 'value':user_id})
            data.append({'name':'userType', 'value':user_type})
            data.append({'name':'name', 'value':username})
            data.append({'name':'accessCode', 'value':password_hash})
            data.append({'name':'dateModified', 'value':user['last_modified']})

            modifier_id = user['modifier_id']
            if modifier_id:
                modifier = g.db.get_user(modifier_id)
                modifier_name = modifier['username']
                data.append({'name':'modifier', 'value':modifier_name})

            if user_type in ['basic', 'admin']:
                archive_id = user['archive_id']
                archive = g.db.get_archive(archive_id)
                if(archive):
                    archive_name = archive['archive_name']
                    link = {'name':archive_name, 'prompt':'Archive accessible by user %s' % username,
                               'rel':'archive','href': api.url_for(Archive, archive=archive_id)}
                    links.append(link)
            elif user_type == 'super':
                archives = g.db.browse_archives()
                for archive in archives:
                    link = {'name':archive['archive_name'], 'prompt':'Archive accessible by user %s' % username,
                               'rel':'archive','href': api.url_for(Archive, archive=archive['archive_id'])}
                    links.append(link)

            # Add new item the the items container in the collection
            items.append(item)

        collection['items'] = items

        # Return the response with status code 200, Collection+JSON mime type and URL to User profile
        return Response (json.dumps(envelope), 200, mimetype=COLLECTIONJSON+";"+USER_PROFILE)

    
    @auth.login_required
    def post(self):
        '''
        Adds a new user to the exam archive. Authorization is required (user must be of type 'super').

        INPUT:

        * `None`

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password. The User must be super admin.

        ENTITY BODY INPUT FORMAT:

        * `Media type`: Collection+JSON:
            http://amundsen.com/media-types/collection/

        * `Profile`: User profile
            http://atlassian.virtues.fi:8090/display/PWP/PWP11#PWP11-Userprofile

        RETURN CODES:

        `201` New user was added successfully.
        `400` Error in request format. Request format does not follow the template.
        `400` Error in request format. Name and accessCode are required.
        `400` Incorrect user type. User type was incorrectly none of the following: basic, admin or super.
        `401` Not logged in. You are not logged in, unable to add new user.
        `403` Access forbidden. You are not authorized. (must be a user of type 'super')
        `409` Error adding new user. User with the same username already exists.
        `415` Unsupported media type. Use a JSON compatible format.
        `500` Database error. Please, contact the administrator.

        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable to add new user")
        if not g.user_logged_in or not g.user_type in ['super']:
            return error_response(403, "Access forbidden", "You are not authorized")

        # Convert the request body to JSON. If it fails get_json method throws an exception. Catch it and report it to
        # the user as an error. Set silent = True to let us replace '400 bad request' with more detailed error message.
        input = request.get_json(force=True, silent=True)

        if not input:
            return error_response(415, "Unsupported media type", "Use a JSON compatible format")

        # Get the date from template. If the template is malformed, catch the exception and report an error.
        try:
            data = input['template']['data']

            # The only required attributes are userId and accessCode
            username = None
            password = None
            archive_id = None
            modifier_id = g.user_logged_in

            # Default user type is 'basic'
            user_type = "basic"
            for d in data:
                #This code has a bad performance. We write it like this for
                #simplicity. Another alternative should be used instead.
                if d['name'] == 'name':
                    username = d['value']
                elif d['name'] == 'userType':
                    user_type = d['value']
                elif d['name'] == 'accessCode':
                    password = d['value']
                elif d['name'] == 'archiveId':
                    archive_id = d['value']
        except:
            #This is launched if either title or body does not exist or if
            # the template.data array does not exist.
            return error_response(400, "Error in request format", "Request format does not follow the template")

        # Check the date is valid
        if not username or not password:
            return error_response(400, "Error in request format", "Name and accessCode are required")
        if not user_type in ['basic', 'admin', 'super']:
            return error_response(400, "Incorrect user type", "User type was incorrectly none of the following: basic, admin or super")

        # Try to create the new user
        try:
            new_user_id = g.db.create_user(username, password, user_type, archive_id, modifier_id)
        except ExamDatabaseErrorExists as e:
            return error_response(409, "Error adding new user", "User with the same username already exists")

        if not new_user_id:
            return error_response(500, "Database error", "Please, contact the administrator")

        # Create the location header with the username of the newly added user
        url = api.url_for(User, username=username)

        # Return the response with status code 201 and location header with URL pointing to new resource
        return Response(status=201, headers={'Location':url}, mimetype=DEFAULTJSON)

# Define the resources
class User(Resource):
    '''
    Resource User implementation
    '''
    
    @auth.login_required
    def get(self, username):
        '''
        Get information of an individual user.

        INPUT:

        * `username` : Identifies the user

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.
        The User must be admin or super admin.

        ENTITY BODY OUTPUT FORMAT:

        * `Media type`: Collection+JSON:
            http://amundsen.com/media-types/collection/

        * `Profile`: User profile
            http://atlassian.virtues.fi:8090/display/PWP/PWP11#PWP11-Userprofile

        RETURN CODES:

        `200` The user information was fetched and returned successfully.
        `401` Not logged in. You are not logged in, unable to get user information.
        `403` Access forbidden. You are not authorized to access the user list.
        `404` User not found. Requested user was not found.
        `409` No userID. Not userID parameter provided.

        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''
        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable to get user information")
        if not g.user_logged_in or (g.user_type in ['basic','admin'] and g.username != username):
            return error_response(403, "Access forbidden", "You are not authorized to access the user list")

        if not username:
            return error_response(409, "No userID", "Not userID parameter provided")

        # Extract users from the database
        user = g.db.get_user_by_name(username)

        if not user:
            return error_response(404, "User not found", "Requested user was not found")

        # Create the envelope
        envelope = {}
        collection = {}
        envelope["collection"] = collection
        collection['version'] = API_VERSION
        collection['href'] = api.url_for(User, username=username)

        collection['template'] = {
            "data" : [
                {"prompt" : "Insert user ID", "name" : "userId", "value" : "", "required":False},
                {"prompt" : "Insert user name", "name" : "name", "value" : "", "required":True},
                {"prompt" : "Insert user type", "name" : "userType", "value" : "", "required":False},
                {"prompt" : "Insert user archive", "name" : "archiveId", "value" : "", "required":False},
                {"prompt" : "Insert user password", "name" : "accessCode", "value" : "", "required":True}
            ]
        }
        collection['links'] = [{'name':'user_list', 'prompt':'All the users in the exam archive',
                                'rel':'users','href': api.url_for(UserList)},
                               {'name':'archive_list', 'prompt':'List of accessible archives',
                                'rel':'archives','href': api.url_for(ArchiveList)}]
        # Create the items
        items = []

        user_id = user['user_id']
        user_type = user['user_type']
        username = user['username']
        archive_id = user['archive_id']
        password_hash = user['password']

        item = {}
        data = []
        links = []
        item['href'] = api.url_for(User, username=username)
        item['read-only'] = True
        item['data'] = data
        item['links'] = links

        # Append proper fields with values to items
        data.append({'name':'userId', 'value':user_id})
        data.append({'name':'userType', 'value':user_type})
        data.append({'name':'name', 'value':username})
        data.append({'name':'accessCode', 'value':password_hash})
        data.append({'name':'archiveId', 'value':archive_id})
        data.append({'name':'dateModified', 'value':user['last_modified']})

        modifier_id = user['modifier_id']
        if modifier_id:
            modifier = g.db.get_user(modifier_id)
            modifier_name = modifier['username']
            data.append({'name':'modifier', 'value':modifier_name})

        if user_type in ['basic', 'admin']:
            archive_id = user['archive_id']
            archive = g.db.get_archive(archive_id)
            if archive:
                archive_name = archive['archive_name']
                link = {'name':archive_name, 'prompt':'Archive accessible by user %s' % username,
                           'rel':'archive','href': api.url_for(Archive, archive=archive_id)}
                links.append(link)
        elif user_type == 'super':
            archives = g.db.browse_archives()
            for archive in archives:
                link = {'name':archive['archive_name'], 'prompt':'Archive accessible by user %s' % username,
                           'rel':'archive','href': api.url_for(Archive, archive=archive['archive_id'])}
                links.append(link)

        items.append(item)

        collection['items'] = items

        # Return the response with status code 200 and Collection+JSON mime type with URL to User profile
        return Response (json.dumps(envelope), 200, mimetype=COLLECTIONJSON+";"+USER_PROFILE)
    
    @auth.login_required
    def put(self, username):
        '''
        Updates user information in the exam archive. 

        INPUT:

        * `username` : Identifies the user to be modified

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.
        The User must be super admin.

        ENTITY BODY INPUT FORMAT:

        * `Media type`: Collection+JSON:
            http://amundsen.com/media-types/collection/

        * `Profile`: User profile
            http://atlassian.virtues.fi:8090/display/PWP/PWP11#PWP11-Userprofile

        RETURN CODES:

        `200` The user information was updated successfully.
        `400` Error in request format. Request format does not follow template.
        `400` Incorrect user type. User type was incorrectly none of the following: basic, admin or super.
        `401` Not logged in. You are not logged in, unable to update user information.
        `403` Access forbidden. You are not authorized. (must be a user of type 'super')
        `404` User not found. Given username was not found.
        `409` Error updating user.
        `415` Unsupported media type. Use a JSON compatible format.
        `500` Database error. Please, contact the adminnistrator.

        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable to update user information")
        if not g.user_logged_in or (g.user_type in ['basic','admin'] and g.username != username):
            return error_response(403, "Access forbidden", "You are not authorized")

        # Extract users from the database
        user = g.db.get_user_by_name(username)

        if not user:
            return error_response(404, "User not found", "Given username was not found")

        # Convert the request body to JSON. If it fails get_json method throws an exception. Catch it and report it to
        # the user as an error. Set silent = True to let us replace '400 bad request' with more detailed error message.
        input = request.get_json(force=True, silent=True)

        if not input:
            return error_response(415, "Unsupported media type", "Use a JSON compatible format")

        # Get the date from template. If the template is malformed, catch the exception and report an error.
        try:
            data = input['template']['data']

            # The only required attributes are userId and accessCode
            username = user['username']
            password = user['password']
            user_type = user['user_type']
            user_id = user['user_id']
            archive_id = user['archive_id']
            modifier_id = g.user_logged_in

            for d in data:
                #This code has a bad performance. We write it like this for
                #simplicity. Another alternative should be used instead.
                if d['name'] == 'name':
                    username = d['value']
                elif d['name'] == 'userType':
                    user_type = d['value']
                elif d['name'] == 'accessCode':
                    password = d['value']
                elif d['name'] == 'archiveId':
                    archive_id = d['value']
        except:
            #This is launched if either title or body does not exist or if
            # the template.data array does not exist.
            return error_response(400, "Error in request format", "Request format does not follow template")

        if not user_type in ['basic', 'admin', 'super']:
            return error_response(400, "Incorrect user type", "User type was incorrectly none of the following: basic, admin or super")

        #Create the new message and build the response code
        try:
            success = g.db.edit_user(user_id, username, password, user_type, archive_id, modifier_id)

        except ExamDatabaseErrorExists as e:
            return error_response(409, "Error updating user", e.message)

        if not success:
            return error_response(500, "Database error", "Please, contact the adminnistrator")

        #Create the Location header with the id of the message created
        url = api.url_for(User, username=username)

        # Return the response with status code 200 and location header
        return Response(status=200, headers={'Location':url}, mimetype=DEFAULTJSON)

    
    @auth.login_required
    def delete(self, username):
        '''
        Delete a user from the exam archive.

        INPUT:

        * `username` : Identifies the user to be modified

        HEADERS:

        * `Accept`: application/json
        * `Authorization`: HTTP basic authentication header with user name and password as specified in RFC 2617.
        The user must be super admin.

        RETURN CODES:

        `204` The user information was updated successfully.
        `401` Not logged in. You are not logged in, unable delete the user.
        `403` Access forbidden. You are not authorized. (must be a user of type 'super')
        `404` User not found. Given username was not found.
        `500` Database error. Please, contact the adminnistrator.

        In case of error, the response media type Problem+JSON is returned with the error message above.
        '''

        if g.no_auth_provided:
            return error_response(401, "Not logged in", "You are not logged in, unable delete the user")
        if not g.user_logged_in or g.user_type != 'super':
            return error_response(403, "Access forbidden", "You are not authorized")

        # Extract users from the database
        user = g.db.get_user_by_name(username)

        if not user:
            return error_response(404, "User not found", "Given username was not found")

        if g.user_type == 'admin' and user['archive_id'] != g.user_archive:
            return error_response(403, "Access forbidden", "You are not authorized")

        # Try to delete the user
        user_id = user['user_id']
        success = g.db.remove_user(user_id)

        if not success:
            return error_response(500, "Database error", "Please, contact the adminnistrator")

        # Return the response
        return Response(status=204, mimetype=DEFAULTJSON)
