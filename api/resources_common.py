# coding=UTF-8
#
# Provides common functions and definitions for the Exam Archive.
#
# @authors: Ari Kairala, Petteri Ponsimaa
# The class is based on code made by Ivan Sanchez (from exercise 4 code of resources.py).


import json

from flask import Flask, request, Response, g, jsonify
from flask.ext.restful import Resource, Api, abort
from flask.ext.httpauth import HTTPBasicAuth
from werkzeug.exceptions import NotFound, UnsupportedMediaType
from functools import wraps
import exam_archive

DEFAULT_DB_PATH = 'db/exam_archive.db'
''' Default path for exam archive SQLite database. '''

# Constants for hypermedia formats and profiles
COLLECTIONJSON = "application/vnd.collection+json"
''' Mime type for Collection+JSON used in all successfull HTTP responses. '''

PROBLEMJSON = "application/problem+json"
''' Mime type for Problem+JSON used for reporting all errors. '''

DEFAULTJSON = "application/json"
''' Mime type for methods returning non-hypermedia mimetype. '''

USER_PROFILE = "http://atlassian.virtues.fi:8090/display/PWP/PWP11#PWP11-Userprofile#PWP11-Userprofile"
''' Link to profile User_profile. '''

ARCHIVE_PROFILE = "http://atlassian.virtues.fi:8090/display/PWP/PWP11#PWP11-Archiveprofile"
''' Link to profile Archive_profile. '''

COURSE_PROFILE = "http://atlassian.virtues.fi:8090/display/PWP/PWP11#PWP11-Courseprofile"
''' Link to profile Course_profile. '''

EXAM_PROFILE = "http://atlassian.virtues.fi:8090/display/PWP/PWP11#PWP11-Examprofile"
''' Link to profile Exam_profile. '''

EXAM_ARCHIVE = "Exam Archive"
''' Name of the RESTful API implementation. '''

API_DOCUMENTATION = "http://atlassian.virtues.fi:8090/display/PWP/PWP11#PWP11-RESTfulAPIdesignandimplementation"
''' Link to the RESTful API documentation. '''

API_VERSION = "1.0"
''' Define the RESTful API version of the Exam Archive. '''

UPLOAD_FOLDER = 'exams'
''' Define the upload folder for the exam files. '''

ALLOWED_EXTENSIONS = ['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif']
''' Define the allowed file extension of the exam files. '''

# Define the application and the API
app = Flask(__name__, static_folder=UPLOAD_FOLDER, static_url_path='')
app.debug = True

# Set the database API and upload folder for exams.
app.config.update({'DATABASE':exam_archive.ExamArchiveDatabase(DEFAULT_DB_PATH)})
app.config.update({'UPLOAD_FOLDER': UPLOAD_FOLDER})

# Start the RESTful API with Flask.
api = Api(app)
auth = HTTPBasicAuth()

def error_response(status_code, title, detail, mimetype=PROBLEMJSON):
    '''
    Helper function for creating error resoponses.

    INPUT:

    * `status_code`: The HTTP status code of an error condition.
    * `title`: The title field of an error.
    * `detail`:  The actual error message returned.
    * `mime_type`: Mime type of the error. If not speficied Mime type 'application/problem+json' is used.
    '''

    # Flask jsonify() function returns flask.Response() object that already has the content-type header
    # 'application/json' for use with json responses
    response = jsonify(title=title, detail=detail, status=status_code, type=API_DOCUMENTATION)
    response.status_code = status_code
    response.mimetype = mimetype
    return response

@app.errorhandler(401)
def access_forbidden(error):
    ''' Error handler for client: status code 401. '''
    return error_response(401, "Forbidden to have access", "You are forbidden to have access to the resource")

@app.errorhandler(404)
def resource_not_found(error):
    ''' Error handler for client: status code 404. '''
    return error_response(404, "Resource not found", "This resource URL does not exist")

@app.errorhandler(500)
def unknown_error(error):
    ''' Error handler for client: status code 500. '''
    return error_response(500, "Error", "The system has failed. Please, contact the administrator")

@app.before_request
def set_database():
    '''
    Stores an instance of the database API before each request in the flask.g variable accessible only from the
    application context.
    '''
    g.db = app.config['DATABASE']

@auth.verify_password
def verify_password(username, password):

    g.user_logged_in = None
    g.user_type = None
    g.user_archive = None
    g.no_auth_provided = False
    g.username = None

    # If the Authentication header is not present Flask HTTPAuth will set username and password to empty strings.
    # In this case, do not prompt for them but rather let resources decide whether anonymous access is allowed.
    if not username and not password:
        g.no_auth_provided = True
        return True

    user_id = g.db.authorize_user(username, password)
    if not user_id:
        return False

    user = g.db.get_user(user_id)
    g.user_logged_in = user_id
    g.user_type = user['user_type']
    g.user_archive = user['archive_id']
    g.username = username
    return True

@auth.error_handler
def access_forbidden():
    ''' Error handler for API: status code 401. '''
    return error_response(401, "Forbidden to have access", "You are forbidden to have access to the resource")

def file_extension(filename):
    return filename.rsplit('.', 1)[1]

def allowed_file(filename):
    return '.' in filename and file_extension(filename) in ALLOWED_EXTENSIONS