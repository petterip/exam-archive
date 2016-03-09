# coding=UTF-8
#
# Provides the database API to access and modify persistent data
# in the Examrium.
#
# @authors: Ari Kairala, Petteri Ponsimaa
# The class is based on code made by Ivan Sanchez (from exercise 2 code of database.py).

import sqlite3
from sqlite3 import IntegrityError
import re
import os
import arrow

# Default paths for .db and .sql files to create and populate the database.
DEFAULT_DB_PATH = 'db/exam_archive.db'
''' Default path for exam archive SQLite database. '''
DEFAULT_SCHEMA = "db/exam_archive_schema_dump.sql"
''' SQL create clauses for creating the database. '''
DEFAULT_DATA_DUMP = "db/exam_archive_data_dump.sql"
''' SQL create and insert clauses for testing. '''

class ExamArchiveDatabase(object):
    '''
    API to access the exam archive database.

    '''

    def __init__(self, db_path=None):
        '''
        db_path is the address of the path with respect to the calling script.
        If db_path is None, DEFAULT_DB_PATH is used instead.
        '''
        super(ExamArchiveDatabase, self).__init__()
        if db_path is not None:
            self.db_path = db_path
        else:
            self.db_path = DEFAULT_DB_PATH

    # Setting up the database. Used for the tests. Setup, populate and delete the database
    def clean(self):
        '''
        Purge the database removing old values.
        '''
        os.remove(self.db_path)

    def load_init_values(self):
        '''
        Populate the database with initial values. 
        '''
        self.create_tables_from_schema()
        self.load_table_values_from_dump()

    def create_tables_from_schema(self, schema=None):
        '''
        Create programmatically the tables from a schema file.
        schema contains the path to the .sql schema file. If it is None,  
        DEFAULT_SCHEMA is used instead. 
        '''
        con = sqlite3.connect(self.db_path)
        if schema is None:
            schema = DEFAULT_SCHEMA
        with open(schema) as f:
            sql = f.read()
            cur = con.cursor()
            cur.executescript(sql)

    def load_table_values_from_dump(self, dump=None):
        '''
        Populate programmatically the tables from a dump file.
        dump is the path to the .sql dump file. If it is None,  
        DEFAULT_DATA_DUMP is used instead.
        '''
        con = sqlite3.connect(self.db_path)
        if dump is None:
            dump = DEFAULT_DATA_DUMP
        with open(dump) as f:
            sql = f.read()
            cur = con.cursor()
            cur.executescript(sql)

    # Helper functions for public database API functions.

    def _create_object(self, row):
        '''
        Create a dictionary object from a table row.

        Source: A simple REST server for Sailors,
        http://www.cs.unc.edu/Courses/comp521-f13/media/L9-InternetApplications2.html
        '''
        return dict(zip(row.keys(), row))

    def _scrub(self, table_name):
        ''' 
        Sanitize a table name that can not be replaced with sqlite3's substitaion.
        E.g. _scrub('); drop tables --') returns 'droptables'
        
        Code snippet by Donald Miner, source: http://stackoverflow.com/questions/3247183/variable-table-name-in-sqlite
        '''
        return ''.join(chr for chr in table_name if chr.isalnum())

    def _valid_foreign_key(self, db_connection, table_name, value):
        '''
        Check if a foreign key is valid and can be found from referencing table.
        '''
        if value is None:
            return True

        # Sanitize the table name before using it
        table_name = self._scrub(table_name)

        # SQL Statement for checking that the user does not yet exist
        sql_query = 'SELECT * from %s WHERE %s_id = ?' % (table_name, table_name)
        pvalue = (value,)
        db_connection.execute(sql_query, pvalue)
        row = db_connection.fetchone()
        if row is not None:
            return True
        else:
            return False

    # Database API - functions to handle database

    def create_archive(self, archive_name, organisation_name, identification_needed=False, modifier_id=None):
        '''
        Create new exam archive to database. An archive is specific to certain 
        faculty or department, for example "Blanko" for Information Processing
        Science faculty of Oulu University.
        
        INPUT:

        * `archive_name`: The name of the archive to be created.
        * `organisation_name`: The name of the organisation, such as faculty, department or school, owning the archive.
        * `identification_needed`:  Whether authorization is required from basic users to view exams.
        * `modifier_id`: The creator or last modifier of the archive or None if not specified.

        OUTPUT:

        * ID of the new archive, if the archive was created successfully, None otherwise.

        Raises exception ExamDatabaseErrorExists, if the an archive already exists with the given archive and
        organisation name.
        Raises exception ExamDatabaseErrorNotFound, if given modifier was not found.
        '''

        # SQL Statement for activating foreign keys
        keys_on = 'PRAGMA foreign_keys = ON'

        # SQL Statement for checking that the archive does not yet exist
        sql_query = 'SELECT * from archive WHERE archive_name = ? AND organisation_name = ?'

        # SQL Statement to create the row in archive table
        sql_insert = 'INSERT INTO archive (archive_name, organisation_name, identification_needed, modifier_id, last_modified) \
        VALUES (?,?,?,?,?)'

        # Get current timestamp and format it into ISO string.
        last_modified = arrow.now().isoformat(' ')

        # Connect to the database and get a connection object
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            # Check that the modifier_id is present in user table
            if not self._valid_foreign_key(cur, "user", modifier_id):
                raise ExamDatabaseErrorNotFound("Modifier does not exist")

            # Execute the statement to find out the archive does not yet exist
            pvalue = (archive_name, organisation_name)
            cur.execute(sql_query, pvalue)
            row = cur.fetchone()
            if row is not None:
                raise ExamDatabaseErrorExists(
                    "Archive already has an entry with the same organisation and archive name")

            # Add the row to archive table by executing the statement
            pvalue = (archive_name, organisation_name, identification_needed, modifier_id, last_modified)
            cur.execute(sql_insert, pvalue)
            lid = cur.lastrowid

            # Return the last row's ID
            return lid


    def create_course(self, archive_id, course_code, course_name, description, teacher_id, url, credit_points,
                      language_id, modifier_id=None):
        '''
        Create an course to the archive. Archive can include multiple courses under same name and other information,
        but there can't be be two courses with same name and language.

        INPUT:
        
        * `archive_id`: ID of the archive where the course belongs to.
        * `course_code`: Code of the course, which is used to identify course for in curriculum.
        * `course_name`: Textual name of the course to be created.
        * `description`: Description of the course.
        * `teacher_id`: ID of the teacher, lecturer or other responsible person of the course.
        * `url`: Course home page URL.
        * `credit_points`: Amount of credit points, that can be earned from the course.
        * `language_id`: Language identifier of the language used in the course.
        * `modifier_id`: The creator or last modifier of the course or None if not specified.

        OUTPUT:

        * ID of the new course entity, if the course was created successfully, None otherwise.

        Raises exception ExamDatabaseErrorExists, if course with given course_name and language_id combination already exists.
        Raises ExamDatabaseErrorNotFound if given archive, teacher, language or modifier were not found in the database.

        '''

        # SQL Statement for activating foreign keys
        keys_on = 'PRAGMA foreign_keys = ON'

        # SQL Statement for checking that the course does not yet exist
        sql_course_query = 'SELECT * from course WHERE course_name = ? AND language_id = ?'

        # SQL Statement to create the row in archive table
        sql_insert = 'INSERT INTO course (archive_id, course_code, course_name, description, teacher_id, url, ' \
                     'credit_points, language_id, modifier_id, last_modified) ' \
                     'VALUES (?,?,?,?,?,?,?,?,?,?)'

        # Get current timestamp and format it into ISO string.
        last_modified = arrow.now().isoformat(' ')

        # Connect to the database and get a connection object
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            # Check that the given user_id exists in the user table
            if not self._valid_foreign_key(cur, "user", modifier_id):
                raise ExamDatabaseErrorNotFound("Modifier does not exist")

            # Check that the given teacher_id exists in the teacher table
            if not self._valid_foreign_key(cur, "teacher", teacher_id):
                raise ExamDatabaseErrorNotFound("Teacher does not exist")

            # Check that the given archive_id exists in the archive table
            if not self._valid_foreign_key(cur, "archive", archive_id):
                raise ExamDatabaseErrorNotFound("Archive does not exist")

            # Check that the given language_id exists in the language table
            if not self._valid_foreign_key(cur, "language", language_id):
                raise ExamDatabaseErrorNotFound("Language does not exist")

            # Execute the statement to find out the archive does not yet exist
            pvalue = (course_name, language_id)
            cur.execute(sql_course_query, pvalue)
            row = cur.fetchone()
            if row is not None:
                raise ExamDatabaseErrorExists("Course already exists with the same name and language")

            # Add the row to archive table by executing the statement
            pvalue = (
                archive_id, course_code, course_name, description, teacher_id, url, credit_points, language_id,
                modifier_id,
                last_modified)
            cur.execute(sql_insert, pvalue)
            lid = cur.lastrowid
            # Return the last row's ID
            return lid


    def create_exam(self, course_id, examiner_id, date, file_attachment, language_id='fi',
                    modifier_id=None):
        '''
        Create an exam and attach it to the given course. A course can be specified by giving either course name or
        course code.

        INPUT:

        * `course_id`: The idenfier of the course, where the exam belongs to
        * `examiner_id`: ID of the teacher, lecturer or other person responsible of overseeing the exam.
        * `date`: Date of the exam given in format of YYYY-MM-DD.
        * `file_attachment`: Identifier for the file attachment.
        * `language_id`: Language identifier for the exam.
        * `modifier_id`: The creator or last modifier of the exam or None if not specified.

        OUTPUT:

        * ID of the new exam entity, if the exam was created successfully, None otherwise.

        Raises exception ExamDatabaseErrorExists, if the an exam already exists with the given date and course,
        Raises exception ExamDatabaseErrorNotFound if course, examiner, language or modifier does not exist.
        Raises exception ValueError if the date is not given in format of YYYY-MM-DD.
        '''

        # Check that the given date string is in valid date format
        try:
            date = arrow.get(date,'YYYY-MM-DD').format('YYYY-MM-DD')
        except:
            raise ValueError('Date must be in format "YYYY-MM-DD"')

        # SQL Statement for activating foreign keys
        keys_on = 'PRAGMA foreign_keys = ON'

        # SQL Statement for checking that the exam does not yet exist
        sql_course_query = 'SELECT * from exam WHERE course_id = ? AND date = ?'

        # SQL Statement to create the row in archive table
        sql_insert = 'INSERT INTO exam (course_id, examiner_id, date, file_attachment, language_id, ' \
                     'modifier_id, last_modified)' \
                     'VALUES (?,?,?,?,?,?,?)'

        # Get current timestamp and format it into ISO string.
        last_modified = arrow.now().isoformat(' ')

        # Connect to the database and get a connection object
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            # Check that the given course_id exists in the course table
            if not self._valid_foreign_key(cur, "course", course_id):
                raise ExamDatabaseErrorNotFound("Course does not exist")

            # Check that the given user_id exists in the user table
            if not self._valid_foreign_key(cur, "user", modifier_id):
                raise ExamDatabaseErrorNotFound("Modifier does not exist")

            # Check that the given examiner_id exists in the teacher table
            if not self._valid_foreign_key(cur, "teacher", examiner_id):
                raise ExamDatabaseErrorNotFound("Examiner does not exist")

            # Check that the given language_id exists in the language table
            if not self._valid_foreign_key(cur, "language", language_id):
                raise ExamDatabaseErrorNotFound("Language does not exist")

            # Execute the statement to find out the archive does not yet exist
            pvalue = (course_id, date)
            cur.execute(sql_course_query, pvalue)
            row = cur.fetchone()
            if row is not None:
                raise ExamDatabaseErrorExists("Exam already exists within the same course and date")

            # Add the row to archive table by executing the statement
            pvalue = (course_id, examiner_id, date, file_attachment, language_id, modifier_id, last_modified)
            cur.execute(sql_insert, pvalue)
            lid = cur.lastrowid

            # Return the last row's ID
            return lid


    def edit_archive(self, archive_id, archive_name, organisation_name, identification_needed=False, modifier_id=None):
        '''
        Update an archive in the database. An archive can be specified by giving archive id.

        INPUT:

        * `archive_id`: ID of the archive to be updated
        * `archive_name`: The name of the archive to be edited.
        * `organisation_name`: The name of the organisation, such as faculty, department or school, owning the archive.
        * `identification_needed`:  Whether authorization is required from basic users to view archive.
        * `modifier_id`: The creator or last modifier of the archive or None if not specified.

        OUTPUT:

        * ID of the archive, if the archive was edited successfully and None if the archive did not exist or there was
        an error updating the database.

        Raises exception ExamDatabaseErrorExists, if the an archive already exists with the given name.
        Raises exception ExamDatabaseErrorNotFound, if given modifier does not exist.
        '''

        # Create the SQL Statements
        # SQL Statement for activating foreign keys
        keys_on = 'PRAGMA foreign_keys = ON'

        # SQL Statement for checking that the archive does exist
        sql_query1 = "SELECT archive_id FROM archive WHERE archive_id = ?"

        # SQL Statement for checking that another archive does not yet exist with the same name and organisation
        sql_query2 = 'SELECT * from archive WHERE archive_id <> ? AND archive_name = ? AND organisation_name = ?'

        sql_update = 'UPDATE archive SET archive_name = ?, organisation_name = ?, identification_needed = ?, ' \
                     'modifier_id = ?, last_modified = ? ' \
                     'WHERE archive_id = ?'

        # Get current timestamp and format it into ISO string.
        last_modified = arrow.now().isoformat(' ')

        # Connect to the database and get a connection object
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            # Execute a query statement to find out whether the archive exists in the database
            pvalue = (archive_id, )
            cur.execute(sql_query1, pvalue)
            # Only one value expected
            row = cur.fetchone()

            # If the archive does not exist, return None
            if row is None:
                return None
            else:
                # Execute a query statement to check that another archive does not yet exist with the same name and organisation
                pvalue = (archive_id, archive_name, organisation_name)
                cur.execute(sql_query2, pvalue)
                # Only one value expected
                row = cur.fetchone()

                # If the archive exists, raise an exception
                if row is not None:
                    raise ExamDatabaseErrorExists(
                        "Another archive already exists with the same archive and organisation name")
                else:
                    # Check that the given modifier_id exists in the user table
                    if not self._valid_foreign_key(cur, "user", modifier_id):
                        raise ExamDatabaseErrorNotFound("Modifier does not exist")

                    # Execute the main update statement
                    pvalue = (archive_name, organisation_name, identification_needed, modifier_id, last_modified,
                              archive_id)
                    cur.execute(sql_update, pvalue)

                    # Check to see that the database was successfully modified
                    if cur.rowcount < 1:
                        return None
                    # Return message id with 'msg-' in the beginning
                    return archive_id


    def edit_course(self, course_id, course_code, course_name, description, teacher_id, url, credit_points, language_id,
                    modifier_id=None):
        '''
        Update an course in the archive identified by a course ID. Archive can include multiple courses under same name 
        and other information, but there cannot be be two courses with same name and language.
        
        INPUT:

        * `course_id`: ID of the course to be updated
        * `course_code`: Code of the course, what is used to identify course for in curriculum.
        * `course_name`: Textual name of the course to be created.
        * `description`: Description of the course.
        * `teacher_id`: Name of the teacher, lecturer or other responsible person of the course.
        * `url`: Course home page URL.
        * `credit_points`: Amount of credit points, that can be earned from the course.
        * `language_id`: Language identifier of the language used in the course.
        * `modifier_id`: The creator or last modifier of the course or None if not specified.
        
        OUTPUT:

        * ID of the course, if the course was updated successfully and None if the course did not exist or there was
        an error updating the database.
        
        Raises exception ExamDatabaseErrorExists, if course with given course_name and language_id combination already 
        exists. Raises ExamDatabaseErrorNotFound, if given teacher, language or modifier does not exist.

        '''

        # Create the SQL Statements
        # SQL Statement for activating foreign keys
        keys_on = 'PRAGMA foreign_keys = ON'

        # SQL Statement for checking that the course does exist and also for fetching the archive_id
        sql_query1 = "SELECT archive_id FROM course WHERE course_id = ?"

        # SQL Statement for checking that another course does not yet exist with the same name and language,
        # within the same archive.
        sql_query2 = 'SELECT * from course WHERE course_id <> ? AND archive_id = ? AND course_name = ? AND ' \
                     'language_id = ?'

        sql_update = 'UPDATE course SET course_code = ?, course_name = ?, description = ?, ' \
                     'teacher_id = ?, url = ?, credit_points = ?, language_id = ?, modifier_id = ?, ' \
                     'last_modified = ? WHERE course_id = ?'

        # Get current timestamp and format it into ISO string.
        last_modified = arrow.now().isoformat(' ')

        # Connect to the database and get a connection object
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            # Execute a query statement to find out whether the course exists in the database
            pvalue = (course_id, )
            cur.execute(sql_query1, pvalue)
            # Only one value expected
            row = cur.fetchone()

            # If the course does not exist, return None
            if row is None:
                return None
            else:
                # Get the course's archive id from the previous query response
                archive_id = row['archive_id']
                # Execute a query statement to check that another course does not yet exist with the same name and language
                pvalue = (course_id, archive_id, course_name, language_id)
                cur.execute(sql_query2, pvalue)
                # Only one value expected
                row = cur.fetchone()

                # If the archive exists, raise an exception
                if row is not None:
                    raise ExamDatabaseErrorExists(
                        "Another course already exists with the same name and language combination")
                else:
                    # Check that the given examiner_id exists in the teacher table
                    if not self._valid_foreign_key(cur, "teacher", teacher_id):
                        raise ExamDatabaseErrorNotFound("Teacher does not exist")

                    # Check that the given modifier_id exists in the user table
                    if not self._valid_foreign_key(cur, "language", language_id):
                        raise ExamDatabaseErrorNotFound("Language does not exist")

                    # Check that the given modifier_id exists in the user table
                    if not self._valid_foreign_key(cur, "user", modifier_id):
                        raise ExamDatabaseErrorNotFound("Modifier does not exist")

                    # Execute the main update statement
                    pvalue = (course_code, course_name, description, teacher_id, url, credit_points,
                              language_id, modifier_id, last_modified, course_id)
                    cur.execute(sql_update, pvalue)

                    # Check to see that the database was successfully modified
                    if cur.rowcount < 1:
                        return None

                    # Everything succeeded * return the course id
                    return course_id


    def edit_exam(self, exam_id, course_id, examiner_id, date, file_attachment, language_id, modifier_id=None):
        '''
        Update an exam in the archive.

        INPUT:

        * `exam_id`: The ID of the exam to be updated
        * `course_id`: The ID of the course where the exam belongs to
        * `examiner_id`: ID of the teacher, lecturer or other person responsible of overseeing the exam.
        * `date`: Date of the exam given in format of YYYY-MM-DD.
        * `file_attachment`: Identifier for the file attachment.
        * `language_id`: Language identifier for the exam.
        * `modifier_id`: The creator or last modifier of the exam or None if not specified.

        OUTPUT:

        * True, if the exam was created successfully, False otherwise.

        Raises exception ExamDatabaseErrorExists, if the an exam already exists with the given course, date and language.
        Raises exception ValueError if the date was not given in format YYYY-MM-DD. Raises ExamDatabaseErrorNotFound if
        course, modifier, language or examiner do not exist.

        '''

        # Check that the given date string is in valid date format
        try:
            date = arrow.get(date,'YYYY-MM-DD').format('YYYY-MM-DD')
        except:
            raise ValueError('Date must be in format "YYYY-MM-DD"')

        # Create the SQL Statements
        # SQL Statement for activating foreign keys
        keys_on = 'PRAGMA foreign_keys = ON'

        # SQL Statement for checking that the exam does exist
        sql_query1 = "SELECT exam_id FROM exam WHERE exam_id = ?"

        # SQL Statement for checking that another exam does not yet exist with the same course, date and language.
        sql_query2 = 'SELECT * from exam WHERE exam_id <> ? AND course_id = ? AND date = ? AND language_id = ?'

        sql_update = 'UPDATE exam SET course_id = ?, examiner_id = ?, date = ?, file_attachment = ?, language_id = ?, ' \
                     'modifier_id = ?, last_modified = ? ' \
                     'WHERE exam_id = ?'

        # Get current timestamp and format it into ISO string.
        last_modified = arrow.now().isoformat(' ')

        # Connect to the database and get a connection object
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            # Execute a query statement to find out whether the exam exists in the database
            pvalue = (exam_id, )
            cur.execute(sql_query1, pvalue)
            # Only one value expected
            row = cur.fetchone()

            # If the course does not exist, return None
            if row is None:
                return None
            else:
                # Execute a query statement to check that another exam does not yet exist within the same course
                # and with the same language
                pvalue = (exam_id, course_id, date, language_id)
                cur.execute(sql_query2, pvalue)
                # Only one value expected
                row = cur.fetchone()

                # If the archive exists, raise an exception
                if row is not None:
                    raise ExamDatabaseErrorExists(
                        "Another exam already exists with the same course, date and language")
                else:
                    # Check that the given course_id exists in the course table
                    if not self._valid_foreign_key(cur, "course", course_id):
                        raise ExamDatabaseErrorNotFound("Course does not exist")

                    # Check that the given examiner_id exists in the teacher table
                    if not self._valid_foreign_key(cur, "teacher", examiner_id):
                        raise ExamDatabaseErrorNotFound("Examiner does not exist")

                    # Check that the given modifier_id exists in the user table
                    if not self._valid_foreign_key(cur, "language", language_id):
                        raise ExamDatabaseErrorNotFound("Language does not exist")

                    # Check that the given modifier_id exists in the user table
                    if not self._valid_foreign_key(cur, "user", modifier_id):
                        raise ExamDatabaseErrorNotFound("Modifier does not exist")

                    # Execute the main update statement
                    pvalue = (course_id, examiner_id, date, file_attachment, language_id, modifier_id,
                              last_modified, exam_id)
                    cur.execute(sql_update, pvalue)

                    # Check to see that the database was successfully modified
                    if cur.rowcount < 1:
                        return None

                    # Everything succeeded - return the exam id
                    return exam_id


    def edit_exam_file(self, exam_id, file_attachment, modifier_id=None):
        '''
        Update an exam file attachment.

        INPUT:

        * `exam_id`: The ID of the exam to be updated
        * `file_attachment`: Identifier for the file attachment.
        * `modifier_id`: The creator or last modifier of the exam or None if not specified.

        OUTPUT:

        * True, if the exam was updated successfully, False otherwise.

        Raises ExamDatabaseErrorNotFound if course, modifier, language or examiner do not exist.

        '''

        # Create the SQL Statements
        # SQL Statement for activating foreign keys
        keys_on = 'PRAGMA foreign_keys = ON'

        # SQL Statement for checking that the exam does exist
        sql_query1 = "SELECT exam_id FROM exam WHERE exam_id = ?"

        sql_update = 'UPDATE exam SET file_attachment = ?, ' \
                     'modifier_id = ?, last_modified = ? ' \
                     'WHERE exam_id = ?'

        # Get current timestamp and format it into ISO string.
        last_modified = arrow.now().isoformat(' ')

        # Connect to the database and get a connection object
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            # Execute a query statement to find out whether the exam exists in the database
            pvalue = (exam_id, )
            cur.execute(sql_query1, pvalue)
            # Only one value expected
            row = cur.fetchone()

            # If the course does not exist, return None
            if row is None:
                return None
            else:
                # Check that the given modifier_id exists in the user table
                if not self._valid_foreign_key(cur, "user", modifier_id):
                    raise ExamDatabaseErrorNotFound("Modifier does not exist")

                # Execute the main update statement
                pvalue = (file_attachment, modifier_id, last_modified, exam_id)
                cur.execute(sql_update, pvalue)

                # Check to see that the database was successfully modified
                if cur.rowcount < 1:
                    return None

                # Everything succeeded - return the exam id
                return exam_id


    # Browsing functions of database API

    def _browse(self, table, parent_id=None, limit=-1, offset=0, offset_represents_ids=False):
        '''
        List all rows in a table, or only the first rows specified by the parameter limit starting from offset.

        INPUT:

        * `table`: table is either 'archive', 'course', 'exam', 'teacher' or 'user'
        * `parent_id`: if table is 'course', parent_id specifies the ID of an archive,
        if table is 'exam', parent_id specified the ID of an course. For archive, the paramenter has not effect
        * `limit`: the maximum length of the list (-1 means no limit)
        * `offset`: skip the amount of offset rows from the beginning, offset being the first returned row
        (zero means to start from the beginning)
        * `offset_represents_ids`: if false, the amount of rows specified by the `offset` parameter are skipped (e.g. for paging). If true, only the XXX are returned having XXX_id greater or equal than `offset`.  the table id (the primary key of the table)
        * `parent_id`: if

        OUTPUT:

        * A list of rows, if one or more rows were found, empty list otherwise. Each row in the list is a
        dictionary containing the same structure as returned by _create_object.

        Raises exception ExamDatabaseError if there was an error accessing the database. Raises exception ValueError
        if table is not archive, course or exam.
        '''

        # Sanitize the table name and based on it, formulate the primary key attribute
        table = self._scrub(table)
        table_id = "%s_id" % table
        pvalue = ()

        if table not in ('archive', 'course', 'exam', 'user', 'teacher'):
            raise ValueError("Given table is not archive, course, exam, user nor teacher")

        # Create the SQL Statement
        keys_on = 'PRAGMA foreign_keys = ON'
        sql_query = 'SELECT * FROM %s' % table
        sql_limit = ''
        sql_where = []

        # If parent_id is speficied, limit the id accordingly:
        # - if table == 'course', add where clause 'WHERE archive_id = <parent_id>'
        # - if table == 'exam', add where clause 'WHERE course_id = <parent_id>'
        if table in ['course', 'exam'] and parent_id is not None:
            if table == 'course':
                sql_where.append('archive_id = ?')
                pvalue = (parent_id,)
            else:
                # table is 'exam'
                sql_where.append('course_id = ?')
                pvalue = (parent_id,)

        # If limit or offset were defined and add WHERE or LIMIT clauses to the query
        if limit > -1 or offset > 0:
            if offset_represents_ids:
                sql_where.append('%s >= ?' % table_id)
                sql_limit = ' LIMIT ?'
                pvalue = pvalue + (offset, limit)
            else:
                # In SQLite, 'LIMIT -1 OFFSET 0' is allowed so we do not need to check
                # whether limit or offset or both of them were defined
                sql_limit = ' LIMIT ? OFFSET ?'
                pvalue = pvalue + (limit, offset)

        # According to PEP 8, empty strings are false
        if sql_where:
            sql_query += ' WHERE ' + ' AND '.join(sql_where)

        # For the time being, sort by primary key (more complex functionality implemented later)
        sql_query += ' ORDER BY %s' % table_id

        if sql_limit:
            sql_query += sql_limit

        # Connect to the database
        con = sqlite3.connect(self.db_path)
        with con:
            #Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()

            #Provide support for foreign keys
            cur.execute(keys_on)

            #Execute main SQL Statement
            cur.execute(sql_query, pvalue)

            #Get results
            rows = cur.fetchall()

            # Build a list of objects containing the table rows
            list = []
            for row in rows:
                obj = self._create_object(row)
                list.append(obj)
            return list

    def browse_archives(self, limit=-1, offset=0, offset_represents_ids=False):
        '''
        List all the archives in the database, or only the first archives specified by the parameters limit and offset.

        INPUT:

        * `limit`: the maximum length of the list (-1 means no limit)
        * `offset`: skip the amount of offset archives from the beginning, offset being the first returned archive
        (zero means to start from the beginning)
        * `offset_represents_ids`: if false, the amount of rows specified by the `offset` parameter are skipped
        (e.g. for paging). If true, only the archives are returned having archive_id greater or equal than `offset`.

        OUTPUT:

        * A list of archives, if one or more archives were found, empty list otherwise. Each archive in the list is a
        dictionary containing the same structure as returned by get_archive.

        '''
        return self._browse("archive", None, limit, offset, offset_represents_ids)

    def browse_courses(self, archive_id, limit=-1, offset=0, offset_represents_ids=False):
        '''
        List all the course in an archive, or only the first courses specified by the parameters limit and offset.

        INPUT:

        * `archive_id`: The ID of an archive
        * `limit`: the maximum length of the list (-1 means no limit)
        * `offset`: skip the amount of offset courses from the beginning, offset being the first returned course
        (zero means to start from the beginning)
        * `offset_represents_ids`: if false, the amount of rows specified by the `offset` parameter are skipped
        (e.g. for paging). If true, only the courses are returned having course_id greater or equal than `offset`.

        OUTPUT:

        * A list of courses, if one or more archives were found, empty list otherwise. Each course in the list is a
        dictionary containing the same structure as returned by get_course.
        '''
        return self._browse("course", archive_id, limit, offset, offset_represents_ids)

    def browse_exams(self, course_id, limit=-1, offset=0, offset_represents_ids=False):
        '''
        List all the exams of a course, or only the first exams specified by the parameters limit and offset.

        INPUT:

        * `course_id`: the ID of the course
        * `limit`: the maximum length of the list (-1 means no limit)
        * `offset`: skip the amount of offset exams from the beginning, offset being the first returned exam
        (zero means to start from the beginning)
        * `offset_represents_ids`: if false, the amount of rows specified by the `offset` parameter are skipped
        (e.g. for paging). If true, only the exams are returned having exam_id greater or equal than `offset`.

        OUTPUT:

        * A list of exams, if one or more archives were found, empty list otherwise. Each exam in the list is a
        dictionary containing the same structure as returned by get_exam.

        '''
        return self._browse("exam", course_id, limit, offset, offset_represents_ids)

    # Get functions of database API

    def _get(self, table, key_value):
        '''
        Get a sigle row from a table.

        INPUT:

        * `table`: table is either 'archive', 'course', 'exam', 'teacher' or 'user'
        * `key_value`: the row where primary key has the value of key_value

        OUTPUT:

        * One rows, if it was found, None otherwise.

        Raises exception ExamDatabaseError if there was an error accessing the database. Raises exception ValueError
        if table is not archive, course or exam.
        '''

        # Sanitize the table name and based on it, formulate the primary key attribute
        table = self._scrub(table)
        table_id = "%s_id" % table

        if table not in ('archive', 'course', 'exam', 'user', 'teacher'):
            raise ValueError("Given table is not archive, course, exam, user nor teacher")

        # Create the SQL Statement
        keys_on = 'PRAGMA foreign_keys = ON'
        sql_query = 'SELECT * FROM %s WHERE %s = ?' % (table, table_id)
        pvalue = (key_value,)

        # Connect to the database
        con = sqlite3.connect(self.db_path)
        with con:
            #Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()

            #Provide support for foreign keys
            cur.execute(keys_on)

            #Execute main SQL Statement
            cur.execute(sql_query, pvalue)

            #Get results
            rows = cur.fetchall()

            # Return the first row found
            for row in rows:
                obj = self._create_object(row)
                return obj

            # Otherwise return None
            return None

    def get_archive(self, archive_id):
        '''
        Get archive details from the database. An archive can be specified by giving archive id.

        INPUT:
        
        * `archive_id`: ID of the archive

        OUTPUT is a dictionary containing the following keys:

        * `archive_name`: The name of the archive
        * `organisation_name`: The name of the organisation, such as faculty, department or school, owning the archive.
        * `identification_needed`:  Whether authorization is required from basic users to view exams.
        * `modifier_id`: The creator or last modifier of the archive or None if not specified.
        * `last_modified`: The date archive was last modified

        If archive was not found, None is returned.

        '''
        return self._get("archive", archive_id)

    def get_archive_by_name(self, archive_name):
        '''
        Find an archive by name. An archive can be specified by giving the full name.

        INPUT:

        * `archive_name`: Name of the archive.

        OUTPUT is a dictionary containing the following keys:

        * `archive_id`: The name of the archive
        * `archive_name`: The name of the archive
        * `organisation_name`: The name of the organisation, such as faculty, department or school, owning the archive.
        * `identification_needed`:  Whether authorization is required from basic users to view exams.
        * `modifier_id`: The creator or last modifier of the archive or None if not specified.
        * `last_modified`: The date archive was last modified

        If archive was not found, None is returned.
        '''

        # SQL Statement for activating foreign keys
        keys_on = 'PRAGMA foreign_keys = ON'

        # SQL Statement for checking that the user does not yet exist
        sql_query = 'SELECT * from archive WHERE archive_name = ?'

        # Connect to the database and get a connection object
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            # Execute the SQL query statement
            pvalue = (archive_name, )
            cur.execute(sql_query, pvalue)
            row = cur.fetchone()

            if row is not None:
                return self._create_object(row)
            else:
                return None

    def get_course(self, course_id):
        '''
        Get course details from the database. A course is specified by giving course id.

        INPUT:
        
        * `course_id`: ID of the course

        OUTPUT is a dictionary containing the following keys:

        * `archive_id`: The ID of an archive where the course belongs to
        * `course_code`: Code of course, which used to to identify course in curriculum
        * `course_name`: Textual name of the course
        * `description`: Description of course
        * `teacher_id`: Responsible teacher of the course
        * `url`: URL address to the course webpage
        * `credit_points`: Number of total credit points earned from course
        * `language_id`: Identifies language used in course
        * `modifier_id`: Creator or last modifie
        * `last_modified`: Last modified date.

        If course was not found, None is returned.
        '''
        return self._get("course", course_id)

    def get_course_by_name(self, course_name):
        '''
        Find course details by course name. A course is specified by giving its full name.

        INPUT:

        * `course_id`: ID of the course

        OUTPUT is a dictionary containing the following keys:

        * `course_id`: The ID of the course
        * `archive_id`: The ID of an archive where the course belongs to
        * `course_code`: Code of course, which used to to identify course in curriculum
        * `course_name`: Textual name of the course
        * `description`: Description of course
        * `teacher_id`: Responsible teacher of the course
        * `url`: URL address to the course webpage
        * `credit_points`: Number of total credit points earned from course
        * `language_id`: Identifies language used in course
        * `modifier_id`: Creator or last modifie
        * `last_modified`: Last modified date.

        If course was not found, None is returned.
        '''

        # SQL Statement for activating foreign keys
        keys_on = 'PRAGMA foreign_keys = ON'

        # SQL Statement for checking that the user does not yet exist
        sql_query = 'SELECT * from course WHERE course_name = ?'

        # Connect to the database and get a connection object
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            # Execute the SQL query statement
            pvalue = (course_name, )
            cur.execute(sql_query, pvalue)
            row = cur.fetchone()

            if row is not None:
                return self._create_object(row)
            else:
                return None

    def get_exam(self, exam_id):
        '''
        Get exam details from the database. An exam is specified by giving exam id.

        INPUT:
        
        * `exam_id`: ID of the exam

        OUTPUT is dictionary containing the following keys:

        * `course_id`: Course ID of the exam
        * `examiner_id`: Responsible teacher of the exam
        * `date`: Date of the exam
        * `file_attachment`: File attachment id of the PDF file
        * `language_id`: Language of the course
        * `modifier_id`: Creator or last modifier
        * `last_modified`: Last modified date

        If exam was not found, None is returned.

        Raises exception ExamDatabaseError if there was an error accessing the database.
        '''
        return self._get("exam", exam_id)

    # Remove functions of the database API

    def remove_archive(self, archive_id):
        '''
        Remove an archive from the database. An archive can be specified by giving archive id. Note: Removing an archive deletes all the courses and all the exams attached to it!

        INPUT:

        * `archive_id`: ID of the archive to be removed

        OUTPUT:

        * If the archive was successfully deleted True is returned, otherwise False.

        '''
        keys_on = 'PRAGMA foreign_keys = ON'
        delete_query = 'DELETE FROM archive WHERE archive_id = ?'

        # Connect to the database
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            #Provide support for foreign keys
            cur.execute(keys_on)
            #Execute the statement to delete
            pvalue = (archive_id,)
            cur.execute(delete_query, pvalue)
            #Check that it has been deleted
            if cur.rowcount < 1:
                return False
            return True


    def remove_course(self, course_id):
        '''
        Remove a course from the database. A course is specified by giving course id. Note: Removing a course deletes all the exams attached to it!

        INPUT:

        * `course_id`: ID of the course

        OUTPUT:

        * If the course successfully deleted True is returned, otherwise False.
        '''

        keys_on = 'PRAGMA foreign_keys = ON'
        delete_query = 'DELETE FROM course WHERE course_id = ?'

        # Connect to the database
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            #Provide support for foreign keys
            cur.execute(keys_on)
            #Execute the statement to delete
            pvalue = (course_id,)
            cur.execute(delete_query, pvalue)
            #Check that it has been deleted
            if cur.rowcount < 1:
                return False
            return True


    def remove_exam(self, exam_id):
        '''
        Remove exam details from the database. An exam is specified by giving exam id. File attachments do not get deleted automatically as they are not part of the database.

        INPUT:

        * `exam_id`: ID of the exam

        OUTPUT:

        * If the exam successfully deleted True is returned, otherwise False.
        '''
        keys_on = 'PRAGMA foreign_keys = ON'
        delete_query = 'DELETE FROM exam WHERE exam_id = ?'

        # Connect to the database
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            #Provide support for foreign keys
            cur.execute(keys_on)
            #Execute the statement to delete
            pvalue = (exam_id,)
            cur.execute(delete_query, pvalue)
            #Check that it has been deleted
            if cur.rowcount < 1:
                return False
            return True

    # Teacher related functions of database API

    def create_teacher(self, first_name, last_name, office='', street_address='', postal_code='', city='', phone='',
                       email='', other_info='', modifier_id=None):
        '''
        Create new teacher entity to the database.

        INPUT:

        * `first_name`: First name (cannot be blank)
        * `last_name`: Last name (cannot be blank)
        * `office`: Office information
        * `street_address`: Street address or P.O.Box
        * `postal_code`: Postal code
        * `city`: City
        * `phone`: Phone number
        * `email`: Email address
        * `other_info`: Other contact information
        * `modifier_id`: Creator or last modifier

        OUTPUT:

        * ID of the new user or None, if there was an error creating new teacher.

        Raises exception ValueError if first_name or last_name were not given, or if email address was malformed.
        '''

        # Validate the parameters
        if not first_name or not last_name:
            raise ValueError("First and last name must be specified for a teacher")

        # Validate the parameters
        if email and not re.match("[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("Teacher's email address is malformed")

        # SQL Statement for activating foreign keys
        keys_on = 'PRAGMA foreign_keys = ON'

        # SQL Statement to create the row in archive table
        sql_insert = 'INSERT INTO teacher (first_name, last_name, office, street_address, postal_code, city, phone, ' \
                     'email, other_info, modifier_id, last_modified) ' \
                     'VALUES (?,?,?,?,?,?,?,?,?,?,?)'

        # Get current timestamp and format it into ISO string.
        last_modified = arrow.now().isoformat(' ')

        # Connect to the database and get a connection object
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            # Check that the modifier_id is present in user table
            if not self._valid_foreign_key(cur, "user", modifier_id):
                raise ExamDatabaseErrorExists("Modifier does not exist")

            # Add the row to archive table by executing the statement
            pvalue = (first_name, last_name, office, street_address, postal_code, city, phone,
                      email, other_info, modifier_id, last_modified)
            cur.execute(sql_insert, pvalue)
            lid = cur.lastrowid

            # Return the last row's ID
            return lid

    def edit_teacher(self, teacher_id, first_name, last_name, office='', street_address='', postal_code='', city='',
                     phone='', email='', other_info='', modifier_id=None):
        '''
        Update teacher details. The teacher is identified by the given teacher ID.

        INPUT:

        * `teacher_id`: The ID of the teacher to be modified.
        * `first_name`: First name (cannot be blank)
        * `last_name`: Last name (cannot be blank)
        * `office`: Office information
        * `street_address`: Street address or P.O.Box
        * `postal_code`: Postal code
        * `city`: City
        * `phone`: Phone number
        * `email`: Email address
        * `other_info`: Other contact information
        * `modifier_id`: Creator or last modifier

        OUTPUT:

        * ID of the updated message, if the user details were modified successfully or None, if not.

        Raises exception ExamDatabaseError if there was an error updating the teacher details.
        Raises exception ValueError if first_name or last_name were not given.
        ExamDatabaseErrorNotFound if modifier does not exist.
        '''

        # Validate the parameters
        if not first_name or not last_name:
            raise ValueError("First and last name must be specified for a teacher")

        # Validate the parameters
        if email and not re.match("[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("Teacher's email address is malformed")

        # Create the SQL Statements
        # SQL Statement for activating foreign keys
        keys_on = 'PRAGMA foreign_keys = ON'

        # SQL Statement for checking that the archive does exist
        sql_query = "SELECT teacher_id FROM teacher WHERE teacher_id = ?"

        sql_update = 'UPDATE teacher SET first_name = ?, last_name = ?, office = ?, street_address = ?, ' \
                     'postal_code = ?, city = ?, phone = ?, email = ?, other_info = ?, modifier_id = ? ' \
                     'WHERE teacher_id = ?'

        # Get current timestamp and format it into ISO string.
        last_modified = arrow.now().isoformat(' ')

        # Connect to the database and get a connection object
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            # Execute a query statement to check that the teacher id exists in the database, if not return None
            pvalue = (teacher_id,)
            cur.execute(sql_query, pvalue)
            # Only one value expected
            row = cur.fetchone()

            # If the teacher row does not exist, return None
            if row is None:
                return None
            else:
                # Check that the given modifier_id exists in the user table
                if not self._valid_foreign_key(cur, "user", modifier_id):
                    raise ExamDatabaseErrorNotFound("Modifier does not exist")

                # Execute the main update statement
                pvalue = (first_name, last_name, office, street_address, postal_code, city, phone, email,
                          other_info, modifier_id, teacher_id)
                cur.execute(sql_update, pvalue)

                # Check to see that the database was successfully modified, otherwise return None
                if cur.rowcount < 1:
                    return None

                # Return taecher id of the updated message
                return teacher_id

    def browse_teachers(self, limit=-1, offset=0, offset_represents_ids=False):
        '''
        List all the teachers in the database, or only the first teachers specified by the parameters limit and offset.

        INPUT:

        * `course_id`: the ID of the course
        * `limit`: the maximum length of the list (-1 means no limit)
        * `offset`: skip the amount of offset exams from the beginning, offset being the first returned exam
        (zero means to start from the beginning)
        * `offset_represents_ids`: if false, the amount of rows specified by the `offset` parameter are skipped
        (e.g. for paging). If true, only the teachers are returned having teacher_id greater or equal than `offset`.

        OUTPUT:

        * A list of exams, if one or more archives were found, empty list otherwise. Each exam in the list is a
        dictionary containing the same structure as returned by _create_object.

        '''
        return self._browse("teacher", None, limit, offset, offset_represents_ids)

    def get_teacher(self, teacher_id):
        '''
        Get teacher details. The teacher is identified by the given teacher ID.

        INPUT:

        * `teacher_id`: The ID of the teacher.

        OUTPUT:

        * `teacher_id`: The ID of the teacher to be modified.
        * `first_name`: First name
        * `last_name`: Last name
        * `office`: Office information
        * `street_address`: Street address or P.O.Box
        * `postal_code`: Postal code
        * `city`: City
        * `phone`: Phone number
        * `email`: Email address
        * `other_info`: Other contact information
        * `modifier_id`: Creator or last modifier
        * `last_modified`: Date when the teacher entity was last modified.

        If the teacher was not found with the given ID, None is returned.
        '''
        return self._get("teacher", teacher_id)

    def get_teacher_by_name(self, first_name, last_name):
        '''
        Find teacher details by teacher name. A teacher is specified by giving its full name.

        INPUT:

        * `teacher_id`: ID of the teacher

        OUTPUT is a dictionary containing the following keys:

        * `teacher_id`: The ID of the teacher to be modified.
        * `first_name`: First name
        * `last_name`: Last name
        * `office`: Office information
        * `street_address`: Street address or P.O.Box
        * `postal_code`: Postal code
        * `city`: City
        * `phone`: Phone number
        * `email`: Email address
        * `other_info`: Other contact information
        * `modifier_id`: Creator or last modifier
        * `last_modified`: Date when the teacher entity was last modified.

        If teacher was not found, None is returned.
        '''

        # SQL Statement for activating foreign keys
        keys_on = 'PRAGMA foreign_keys = ON'

        # SQL Statement for checking that the user does not yet exist
        sql_query = 'SELECT * from teacher WHERE first_name = ? AND last_name = ?'

        # Connect to the database and get a connection object
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            # Execute the SQL query statement
            pvalue = (first_name, last_name)
            cur.execute(sql_query, pvalue)
            row = cur.fetchone()

            if row is not None:
                return self._create_object(row)
            else:
                return None

    def remove_teacher(self, teacher_id):
        '''
        Remove a teacher from the database.

        INPUT:

        * `teacher_id`: ID of the teacher to be deleted.

        OUTPUT:

        * True, if a teacher with the given user_id was found, False otherwise.

        Returns true, if the delete succeeded, otherwise false if there was an error deleting the teacher from the database.
        '''


        keys_on = 'PRAGMA foreign_keys = ON'
        delete_query = 'DELETE FROM teacher WHERE teacher_id = ?'

        # Connect to the database
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            #Execute the statement to delete
            pvalue = (teacher_id,)
            cur.execute(delete_query, pvalue)

            #Check that it has been deleted
            if cur.rowcount < 1:
                return False
            return True


    # User handling functions of database API
    def create_user(self, username, password, user_type='basic', archive_id=None, modifier_id=None):
        '''
        Create new user to database. The user_type can be one of the following:

        * 'basic': The user has only view access to archive specified by archive_id
        * 'admin': The user has read-write access to archive specified by archive_id
        * 'super': The user has read-write access to all the archives in the database.

        INPUT:

        * `username`: Visible username.
        * `password`: Hashed password of the user.
        * `user_type`: User type identifies whether the user is superuser, admin or regular view-only user. The user_type must be one of the values 'super', 'admin' or 'basic'.
        * `archive_id`: The ID of an archive where the user has access to.
        * `modifier_id`: The creator or of the user or None if not specified.

        OUTPUT:

        * ID of the new user.

        Raises exception ExamDatabaseErrorExists, if user with the same username already exists, given archive or modifier does not exist.
        ExamDatabaseErrorNotFound if archive or modifier do not exist.
        Raises exception ValueError if the user_type was not one of the defined values.
        '''

        # Validation of user type
        if user_type not in ['basic', 'admin', 'super']:
            raise ValueError("User type is not basic, admin or super")

        # SQL Statement for activating foreign keys
        keys_on = 'PRAGMA foreign_keys = ON'

        # SQL Statement for checking that the user does not yet exist
        sql_query = 'SELECT * from user WHERE username = ?'

        # SQL Statement to create the row in archive table
        sql_insert = 'INSERT INTO user (username, password, user_type, archive_id, modifier_id, last_modified) \
        VALUES (?,?,?,?,?,?)'

        # Get current timestamp and format it into ISO string.
        last_modified = arrow.now().isoformat(' ')

        # Connect to the database and get a connection object
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            # Check that the given archive_id exists in the archive table
            if not self._valid_foreign_key(cur, "archive", archive_id):
                raise ExamDatabaseErrorNotFound("Archive does not exist")

            # Check that modifier_id exists in the user table
            if not self._valid_foreign_key(cur, "user", modifier_id):
                raise ExamDatabaseErrorNotFound("Modifier does not exist")

            # Execute the statement to find out the username does not exists yet
            pvalue = (username,)
            cur.execute(sql_query, pvalue)
            row = cur.fetchone()
            if row is not None:
                raise ExamDatabaseErrorExists("The given username already exists")

            # Add the row to archive table by executing the statement
            pvalue = (username, password, user_type, archive_id, modifier_id, last_modified)
            cur.execute(sql_insert, pvalue)
            lid = cur.lastrowid
            # Return the last row's ID
            return lid

    def edit_user(self, user_id, username, password, user_type='basic', archive_id=None, modifier_id=None):
        '''
        Update user details. The user is identified by the given user ID.

        INPUT:

        * `user_id`: The ID of the user to be modified.
        * `username`: Visible username.
        * `password`: Hashed password of the user.
        * `user_type`: User type identifies whether the user in superuser, admin or regular view-only user. The user_type must be one of the values 'super', 'admin' or 'basic'.
        * `archive_id`: The ID of an archive where the user has access to.
        * `modifier_id`: The creator or of the user or None if not specified.

        OUTPUT:

        * True, if the user details were modified successfully or False, if not.

        Raises exception ExamDatabaseErrorExists, if user with the same username already exists. Raises exception ExamDatabaseError if there was an error creating new user.
        ExamDatabaseErrorNotFound if modifier does not exist.
        Raises exception ValueError if the user_type was not one of the defined values.
        '''

        # Create the SQL Statements
        # SQL Statement for activating foreign keys
        keys_on = 'PRAGMA foreign_keys = ON'

        # SQL Statement for checking that the user does exist
        sql_query1 = "SELECT user_id FROM user WHERE user_id = ?"

        # SQL Statement for checking that another user does not yet exist with the same username
        sql_query2 = 'SELECT * from user WHERE user_id <> ? AND username = ?'

        # Validation of user type
        if user_type not in ['basic','admin','super']:
            raise ValueError("User type is not basic, admin or super")

        sql_update = 'UPDATE user SET user_type = ?, username = ?, password = ?, ' \
                     'modifier_id = ?, last_modified = ?, archive_id = ? ' \
                     'WHERE user_id = ?'

        # Get current timestamp and format it into ISO string.
        last_modified = arrow.now().isoformat(' ')

        # Connect to the database and get a connection object
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            # Execute a query statement to find out whether the user exists in the database
            pvalue = (user_id, )
            cur.execute(sql_query1, pvalue)
            # Only one value expected
            row = cur.fetchone()

            # If the user does not exist, return None
            if row is None:
                return None

            else:
                # Check that the given modifier_id exists in the user table
                if not self._valid_foreign_key(cur, "user", modifier_id):
                    raise ExamDatabaseErrorNotFound("Modifier does not exist")

                try:
                    # Execute the main update statement
                    pvalue = (user_type, username, password, modifier_id, last_modified, archive_id, user_id)
                    cur.execute(sql_update, pvalue)
                except IntegrityError:
                    # Expect IntegrityError risen when new username already exists in the database
                    raise ExamDatabaseErrorExists("The given username already exists")

                # Check to see that the database was successfully modified
                if cur.rowcount < 1:
                    return None

                return user_id

    def browse_users(self, limit=-1, offset=0, offset_represents_ids=False):
        '''
        List all the users in the database, or only the first users specified by the parameters limit and offset.

        INPUT:

        * `limit`: the maximum length of the list (-1 means no limit)
        * `offset`: skip the amount of offset users from the beginning, offset being the first returned user
        (zero means to start from the beginning)
        * `offset_represents_ids`: if false, the amount of rows specified by the `offset` parameter are skipped
        (e.g. for paging). If true, only the users are returned having user_id greater or equal than `offset`.

        OUTPUT:

        * A list of users, if one or more users were found, empty list otherwise. Each user in the list is a
        dictionary containing the same structure as returned by get_user.

        '''
        return self._browse("user", None, limit, offset, offset_represents_ids)

    def get_user(self, user_id):
        '''
        Get user details. The user is identified by the given user ID.

        INPUT:

        * `user_id`: The ID of the user.

        OUTPUT:

        * `username`: Visible username.
        * `password`: Hashed password of the user.
        * `user_type`: User type identifies whether the user in superuser, admin or regular view-only user. The user_type is one of values 'super', 'admin' or 'basic'.
        * `archive_id`: The ID of an archive where the user has access to.
        * `modifier_id`: The creator or of the user or None if not specified.

        If the user was not found with the given ID, None is returned.
        '''
        return self._get("user", user_id)

    def get_user_by_name(self, username):
        '''
        Find user details by user name.

        INPUT:

        * `user_name`: Visible username

        OUTPUT is a dictionary containing the following keys:

        * `user_id`: ID of the user.
        * `username`: Visible username.
        * `password`: Hashed password of the user.
        * `user_type`: User type identifies whether the user in superuser, admin or regular view-only user. The user_type is one of values 'super', 'admin' or 'basic'.
        * `archive_id`: The ID of an archive where the user has access to.
        * `modifier_id`: The creator or of the user or None if not specified.

        If user was not found, None is returned.
        '''

        # SQL Statement for activating foreign keys
        keys_on = 'PRAGMA foreign_keys = ON'

        # SQL Statement for checking that the user does not yet exist
        sql_query = 'SELECT * from user WHERE username = ?'

        # Connect to the database and get a connection object
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            # Execute the SQL query statement
            pvalue = (username, )
            cur.execute(sql_query, pvalue)
            row = cur.fetchone()

            if row is not None:
                return self._create_object(row)
            else:
                return None

    def authorize_user(self, username, password):
        '''
        Check if a user can be authorized with a given username and password.

        INPUT:

        * `username`: Visible username.
        * `password`: Hashed password of the user.

        OUTPUT:

        * If the username and password were correct, user ID is returned, otherwise None.
        '''

        # SQL Statement for activating foreign keys
        keys_on = 'PRAGMA foreign_keys = ON'

        # SQL Statement for checking that the user does not yet exist
        sql_query = 'SELECT user_id from user WHERE username = ? AND password = ?'

        # Connect to the database and get a connection object
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            # Execute the SQL query statement
            pvalue = (username, password)
            cur.execute(sql_query, pvalue)
            row = cur.fetchone()

            if row is not None:
                return row['user_id']
            else:
                return None

    def user_has_access(self, user_id, archive_id):
        '''
        Check whether a user has access to a specified archive. The user is identified by the given user ID and archive by the given archive ID.

        INPUT:
        * `user_id`: The ID of the user.
        * `archive_id`: The ID of the archive.
        * `identification_needed`: Identification to the archive needed, true or false

        OUTPUT:
        * If the user is authorized to access the given archive, True is returned, otherwise False is returned. False is returned also, if the given user_id or archive_id does not exist. If the user is a superuser and an archive exists, True is always returned.

        '''
        # SQL Statement for activating foreign keys
        keys_on = 'PRAGMA foreign_keys = ON'

        # SQL Statement fr checking that is the user an superuser
        sql_query1 = 'SELECT user_type FROM user WHERE user_id = ?'

        # Connect to the database and get a connection object
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            # Execute the SQL query statement
            pvalue = (user_id,)
            cur.execute(sql_query1, pvalue)
            row = cur.fetchone()

            # If user is an superuser, just continue
            if row['user_type']  == 'super':
                return True
            # If user is not an superuser, continue with identification
            else:
                 # SQL Statement for checking that is identification to the archive needed
                sql_query2 = 'SELECT identification_needed FROM archive WHERE archive_id = ?'

                # Connect to the database and get a connection object
                con = sqlite3.connect(self.db_path)
                with con:
                    # Cursor and row initialization
                    con.row_factory = sqlite3.Row
                    cur = con.cursor()
                    # Provide support for foreign keys
                    cur.execute(keys_on)

                    # Execute the SQL query statement
                    pvalue = (archive_id,)
                    cur.execute(sql_query2, pvalue)
                    row = cur.fetchone()

                    # If user has access, continue with True
                    if row is None:
                        return False

                    # If identification to the archive is needed, identify the user
                    if int(row['identification_needed']) == True:

                        # SQL Statement for checking user's access to the archive
                        sql_query3 = 'SELECT user_id, archive_id FROM user WHERE user_id = ? AND archive_id = ?'

                        # Connect to the database and get a connection object
                        con = sqlite3.connect(self.db_path)
                        with con:
                            # Cursor and row initialization
                            con.row_factory = sqlite3.Row
                            cur = con.cursor()
                            # Provide support for foreign keys
                            cur.execute(keys_on)

                            # Execute the SQL query statement
                            pvalue = (user_id, archive_id)
                            cur.execute(sql_query3, pvalue)
                            row = cur.fetchone()

                            # If user has access, continue with True
                            if row is not None:
                                return True
                            # Else False
                            else:
                                return False

                    # If identification is not needed, just continue
                    else:
                        return True

    def remove_user(self, user_id):
        '''
        Remove user from the database.

        INPUT:

        * `user_id`: ID of the user to be deleted.

        OUTPUT:

        * True, if a user with the given user_id was removed, False otherwise.

        Returns true, if the delete succeeded, otherwise false if there was an error deleting the user from the database.
        '''
        keys_on = 'PRAGMA foreign_keys = ON'
        delete_query = 'DELETE FROM user WHERE user_id = ?'

        # Connect to the database
        con = sqlite3.connect(self.db_path)
        with con:
            # Cursor and row initialization
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            # Provide support for foreign keys
            cur.execute(keys_on)

            #Execute the statement to delete
            pvalue = (user_id,)
            cur.execute(delete_query, pvalue)

            #Check that it has been deleted
            if cur.rowcount < 1:
                return False
            return True

class ExamDatabaseError(Exception):
    '''
    Exception for general exam archive database error.
    '''
    pass

class ExamDatabaseErrorExists(Exception):
    '''
    Exception for an error, when an entity already exists in the database.
    '''
    pass

class ExamDatabaseErrorNotFound(Exception):
    '''
    Exception for an error, when a given entity was not found from the database.
    '''
    pass
