# coding=UTF-8
#
# Server functionality of Exam Archive RESTful API.
#
# @authors: Ari Kairala, Petteri Ponsimaa
# The class is based on code made by Ivan Sanchez (from exercise 4 code of resources.py).

import os

from flask import Flask, request, Response, g, jsonify, send_from_directory, send_file
from werkzeug import secure_filename
from resources_common import app, api
from user_resource import User, UserList
from archive_resource import Archive, ArchiveList
from course_resource import Course, CourseList
from exam_resource import Exam, ExamList, ExamUpload

DEFAULT_DB_PATH = 'db/exam_archive.db'
''' Default path for exam archive SQLite database. '''

# Define the routes for User and UserList resources
api.add_resource(UserList, '/exam_archive/api/users/',
                 endpoint='userlist')
api.add_resource(User, '/exam_archive/api/users/<username>/',
                 endpoint='user')

# Define the routes for Archive and ArchiveList resources
api.add_resource(ArchiveList,   '/exam_archive/api/archives/',
                 endpoint='archivelist')
api.add_resource(Archive,       '/exam_archive/api/archives/<int:archive>/',
                 endpoint='archive')

# Define the routes for Course and CourseList resources
api.add_resource(CourseList,    '/exam_archive/api/archives/<int:archive_id>/courses/',
                 endpoint='courselist')
api.add_resource(Course,        '/exam_archive/api/archives/<int:archive_id>/courses/<int:course_id>/',
                 endpoint='course')

# Define the routes for Exam, ExamList and ExamUpload resources
api.add_resource(ExamList,      '/exam_archive/api/archives/<int:archive_id>/courses/<int:course_id>/exams/',
                 endpoint='examlist')
api.add_resource(Exam,          '/exam_archive/api/archives/<int:archive_id>/courses/<int:course_id>/exams/<int:exam_id>/',
                 endpoint='exam')
api.add_resource(ExamUpload,    '/exam_archive/api/archives/<int:archive_id>/courses/<int:course_id>/exams/<int:exam_id>/upload/',
                 endpoint='examupload')

# Serve pdf files from static location
@app.route('/exams/<path:filename>')
def download_file(filename):
    upload_folder = app.config['UPLOAD_FOLDER']
    return send_file(os.path.join(upload_folder, secure_filename(filename)), as_attachment=True)

# Start the application
if __name__ == '__main__':
    # Activate automatic code reloading and improved error messages
    app.run(debug=True)
