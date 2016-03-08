# Examrium

Originally created by <a href="https://github.com/petterip">petterip</a> & <a href="https://github.com/akairala">akairala</a> in spring 2015.

Examrium offers users to archive previous exams of courses of an university or other educational institute to a Web service, where they are available to be searched and downloaded by students. Users of Examrium are divided in three types: Super admins, Admins and Basic users. Super admins are administrators of whole application and can divide courses in groups by creating archives, which can represent for example a faculty, department or field of study, which makes our application more suitable for different kind of organisations levels. Admins can act as administrators of a single archive, where they can edit course information, create new courses and add exams with PDF attachment under them. It is also possible to store detailed information about a single course and exam, like course code, name, credit points, teacher, language, course website, description and exam date. Basic users can access to single archive, view courses and download exams of them as PDF-file. All user types can also edit their own profile, but only Super admins can edit, remove and create new users. 

Web application is implemented by using single HTML-file as barebone, that is dynamically populated with Javascript. Layout of UI generated with Boostrap-framework. RESTful API in the Examrium is used to handle information between client application and SQlite-database. The implementation of API consists from nine resources, which are divided in their own Python files: user_resource.py, archive_resource.py, course_resource.py and exam_resource.py. Note, that teacher and language resources are not implemented in application within the course and so necessary data about them in UI is rendered with JSON (teacher.json, language.json). Uploading PDF files and authentication of a user is also handled with RESTful API.

The Examrium repository contains:

* **db** - A database schema, database dump and a sample database for testing 
* **documentation** - Documentation for ExamArchiveDatabase class
* **api** - ExamArchiveDatabase source code
* ***api/exams*** The upload folder of exam PDFs (created by the web client)
* **test** - Test suites for ExamArchiveDatabase and the implemented resources
* ***client*** - The web client forming the user interface of Exam Achive
* ***client/ui*** - Static files of the web client
* ***client/ui/css*** - The web client's style sheets
* ***client/ui/js*** - The web client's Javascript logic
* ***client/ui/data*** - Template files used by the web client (languages, user types and teachers)

## Dependencies

Examrium has been tested with Python 2.9.7. The package exam_archive, tests and documentation has following dependencies on external packages:

* **SQLite3**: For database management
* **UnitTest** and **PyTest**: For testing
* **Arrow**: For date and time functions, v0.5.4 available [here](https://github.com/crsmithdev/arrow/)
* **Flask**: For managing HTTP requests and responses, v0.10.1 available [here](http://github.com/mitsuhiko/flask/)
* **Flask-RESTful**: For handling RESTful resources and API functionality, v0.3.2 available [here](https://www.github.com/flask-restful/flask-restful/)
* **Flask-HTTPAuth**: For authenticating user of the API with HTTP Basic authentication, version v2.5.0 available [here](http://github.com/miguelgrinberg/flask-httpauth/)
* **Werkzeug**: For API related exceptions and security related utilities, version v0.10.4 available [here](http://werkzeug.pocoo.org/)
* **json**: For converting JSON media type objects
* **os**: For file transfer related functions
* **pdoc**: For documentation generation, v0.3.1 available [here](https://github.com/BurntSushi/pdoc) (used for make_documentation.py)
  
These external libraries can be installed using pip Python package manager:

```python
    pip install sqlite3 unittest arrow pdoc flask flask-restful flask-httpauth
```

External front-end libraries and frameworks:

* **Bootstrap**, version 3.3.4: HTML, CSS and JavaScrpt framework used for creating responsive layout for web application.
* **HTML5Shiv**: JavaScript library to enable styling of HTML5 elements in versions of Internet Explorer prior to version 9, which do not allow unknown elements to be styled without JavaScript.
* **JQuery**, version 1.11.2: Used for dynamically creating user interface of the web client.
* **CryptoJS**, version 3.1.2: Used for hashing user passwords with SHA-256-algorithm.


## Starting the server

To run the server with included web client, please enter to following command:

```python
    python run.py
```

After this you can access the client with your browser at the following address:
* http://localhost:8080/client/index.html

The included database has three user accounts available for testing. You may login in with one of the supplied user accounts:

```python
User name: bigboss (super user)
Password: ultimatepw

User name: antti.admin (admin)
Password: qwerty1234

User name: testuser (basic user)
Password: testuser
```

## RESTful API

The RESTful API user list is available at following address (the entrypoint):

* http://localhost:8080/exam_archive/api/users/

The RESTful API archive list is available at following address:

* http://localhost:8080/exam_archive/api/archives/

The API requires HTTP Basic authentication. The following accounts are supplied:

```python
User name: bigboss (super user)
Password: 421c11091311963998d4c1c1b77d53b36967e9d111bec0f9760f7812dd151f88

User name: antti.admin (admin)
Password: 17f80754644d33ac685b0842a402229adbb43fc9312f7bdf36ba24237a1f1ffb

User name: testuser (basic user)
Password: ae5deb822e0d71992900471a7199d0d95b8e7c9d05c40a8245a281fd2c1d6684
``` 


## Using ExamArchiveDatabase in our own code
In case you want to use ExamArchiveDatabase class directly in your code instead of making use of the RESTful APIclass, 
make sure the file exam_archive.py is in your PYTHONPATH and import it with following statement:

```python
    import exam_archive
``` 

To initialize the SQLite database with sample data (e.g. for testing purposes), run the following commands from Python shell:

```python
    import exam_archive
    db = exam_archive.ExamArchiveDatabase('db/exam_archive.db')
    db.clean()
    db.load_table_values_from_dump()
```

See exam_archive.html in documentation folder for more information how to use the class. Documentation can be regenerated by running make_documentation.py script:

```python
    python make_documentation.py
``` 

## Making use of RESTful API
The Exam Achive has 8 resources and following HTTP requests can be made for fetching, creating and modifying the resources:

* **UserList** resource lets the admin list all the user in the system and create a new user
    * **GET** gets a list of users
    * **POST** creates a new user 
* **User** resource lets the user to get information about single user, modify and delete him/her
    * **GET** get user information	
    * **PUT** updates user information	
    * **DELETE** delete a user	
* **ArchiveList** resource lets the user list and create new archives
    * **GET** gets a list of accessible archives	
    * **POST** creates a new archive
* **Archive** resource lets the user get information about single archive, modify and delete it
	* **GET** gets archive details	
	* **PUT** modifies archive details	
	* **DELETE** deletes an archive
* **CourseList** resource lets the user list and create new courses
    * **GET** gets a list of accessible courses	
    * **POST** creates a new course
* **Course** resource lets the user get information about single course, modify and delete it
	* **GET** gets course details
	* **PUT** updates course details
	* **DELETE** deletes a course
* **Exam list** resource lets the user list and create exams
    * **GET** gets a list of accessible exams
    * **POST** creates a new exam
* **Exam** resource lets the user get information about single exam, modify and delete it
    * **GET** get exam details	
    * **PUT** updates exam details
    * **DELETE** deletes an exam
* **ExamUpload** resource lets the user to upload a PDF file and attach it to an exam
    * **GET** retrieve exam file URL
    * **POST** upload exam file and attach it to an exam

The documentation of the classes include more detailed list on how to use the HTTP requests and their responses including status codes:
[user_resource.html](http://atlassian.virtues.fi:8090/download/attachments/13304318/user_resource.html), 
[archive_resource.html](http://atlassian.virtues.fi:8090/download/attachments/13304318/archive_resource.html), 
[course_resource.html](http://atlassian.virtues.fi:8090/download/attachments/13304318/course_resource.html) and 
[exam_resource.html](http://atlassian.virtues.fi:8090/download/attachments/13304318/exam_resource.html).


## Hypermedia

The RESTful API implementation makes use of two media types, 
[Collection+JSON](http://amundsen.com/media-types/collection/format/) and 
[Problem+JSON](https://tools.ietf.org/html/draft-ietf-appsawg-http-problem-00). All the resources User, 
UserList, Archive, ArchiveList, Course, CourseList and Exam, ExamList make use of media type Collection+JSON. 
The format of the media type is defined in detail [here](http://amundsen.com/media-types/collection/format/).
 
When a request fails, RESTful API returns a response of media type Problem+JSON. The media type defines a 
"problem detail" as a way to carry details of errors in a HTTP response, to avoid the need to reinvent new error 
response formats for HTTP APIs. It is a HTTP response carrying JSON problem details, the canonical model for problem 
details is a JSON object. When serialised as a JSON document, that format is identified with the 
"application/problem+json" media type. The format of the media type is defined in detail 
[here](https://tools.ietf.org/html/draft-ietf-appsawg-http-problem-00).

## Profiles

## 1. User profile

User profile describes link relations and semantic descriptors for a super, admin and basic users in the exam archive.

#### Dependencies
This profile inherits some semantic descriptors from:

* http://schema.org/Person
* http://schema.org/Text

Furthermore some of the semantic descriptors use the following standards
ISO 8601 (Date and Time format). More info [here](http://en.wikipedia.org/wiki/ISO_8601).

#### Link relations
* **ArchiveList**. An archive or list of archives where the user has access to. Each item in the list is an instance of the type Archive defined in the profile Archive_profile. Can only be accessed with GET.

**Data type User**: A person who is registered in the exam archive. The user data type extends schema.org/Person. User contains the following properties:

* name: String. Visible username. Inherited from schema.org/Person.
* userId: Integer. The ID of the user.
* accessCode: String. Hashed password of the user. Inherited from http://schema.org/Text.
* userType: String. User type identifies whether the user in superuser, admin or regular view-only user. The user_type must be one of the values 'super', 'admin' or 'basic'.
* archiveId: Integer. The ID of an archive where the user has access to (used only for user types of 'basic' and 'admin').
* modifierId: Integer. The creator or of the user or None if not specified.
* dateModified: Date. The date when the user was created of last modified. Presented in ISO 8601 format.

## 2. Archive profile

Archive profile describes link relations and semantic descriptors for an archive in the exam archive. An archive is a 
resource containing collections of other resources, namely courses. In practice an archive is an faculty, department, 
school or student organization such as Blanko, SIK or OTiT.

#### Dependencies
This profile inherits some semantic descriptors from: http://schema.org/Dataset. 
Furthermore some of the semantic descriptors use the following standards ISO 8601 (Date and Time format). 
More info [here](http://en.wikipedia.org/wiki/ISO_8601)

#### Link relations

* **TeacherList**. List of teachers in the archive. The links is visible only to super admin. Each item in the list is 
an instance of type User defined in the profile User_profile. Can be accessed only with GET. _Not implemented since 
TeacherList is not part of the course implementation._
* **CourseList** List of courses in the archive. Each item in the list is an instance of type Course defined in the 
profile Course_profile. Can be accessed only with GET.

**Data type Archive**: An archive in the exam archive. The archive data type extends schema.org/Dataset. Archive contains the following properties:

* name: String. The name of the archive. Inherited from schema.org/Dataset.
* archiveId: Integer. The ID of an archive.
* organisationName: String. The name of the organisation, such as faculty, department or school, owning the archive.
* identificationNeeded: Boolean. Whether authorization is required from basic users to view exams.
* modifierId: Integer. The creator or of the user or None if not specified.
* dateModified: Date. The date when the user was created of last modified. Presented in ISO 8601 format. Inherited from schema.org/Dataset.
 
## 3. Course profile

Course profile describes link relations and semantic descriptors for a course in an archive. 

#### Dependencies
This profile inherits some semantic descriptors from:

* http://schema.org/Article
* http://schema.org/Thing

Furthermore some of the semantic descriptors use the following standards
ISO 8601 (Date and Time format). More info [here](http://en.wikipedia.org/wiki/ISO_8601)

#### Link relations

* **TeacherList**. Link to teacher of the course. The links is visible only to super admin. Each item in the list is 
an instance of type User defined in the profile User_profile. Can be accessed only with GET.
exams. List of exams of the course. Each exam in the list is an instance of type Exam defined in the profile Exam 
profile. Can be accessed only with GET. _Not implemented since TeacherList is not part of the course implementation._

**Data type Course**: A course within an archive in the exam archive. The course data type extends schema.org/Article. Course contains the following properties:

* name: String. The name of the course. Inherited from schema.org/Article.
* archiveId: Integer. ID of the archive where the course belongs to.
* courseCode: String. Code of the course, what is used to identify course for in curriculum.
* description: String. Description of the course. Inherited from schema.org/Thing.
* teacherId: Integer. ID of the teacher, lecturer or other responsible person of the course.
* url: String. Course home page URL. Inherited from schema.org/Article.
* creditPoints: Integer. Amount of credit points, that can be earned from the course.
* inLanguage: String. Language identifier of the language used in the course. Inherited from schema.org/Article.
* modifierId: Integer. The creator or last modifier of the course
* dateModified: Date. The date when the user was created of last modified. Presented in ISO 8601 format. Inherited from schema.org/Article.

## 4. Exam profile

Exam profile describes link relations and semantic descriptors for a course in an archive. An exam represents a single exam in the exam archive. It has the actual exam presented in PDF or images format and the date when the exam took place. 

#### Dependencies
This profile inherits some semantic descriptors from:

* http://schema.org/Article

Furthermore some of the semantic descriptors use the following standards
ISO 8601 (Date and Time format). More info [here](http://en.wikipedia.org/wiki/ISO_8601).

#### Link relations

* **Teacher**. Examiner of the archive. The links is visible only to super admin. Each item in the list is an instance 
of type User defined in the profile User_profile. Can be accessed only with GET.
exams. List of other exams in the course. Each item in the list is an instance of type Exam defined in the profile 
Exam_profile. Can be accessed only with GET. _Not implemented since 
Teacher resource is not part of the course implementation._

**Data type Exam**: An exam represents a single exam in the exam archive. The exam data type extends schema.org/Article. Exam contains the following properties:

* name: String. The course name. Inherited from schema.org/Article.
* examId: Integer. The ID of the exam.
* courseCode: String. The identifier code for the course. One of the following parameters must be given, either course code or course name.
* examinerId: Integer. ID of the teacher, lecturer or other person responsible of overseeing the exam.
* date: Date. The date of the exam given in format of YYYY-MM-DD.
* associatedMedia: String. URL to the PDF file of an exam. Inherited from schema.org/Article.
* inLanguage: String. Language identifier for the exam. Inherited from schema.org/Article.
* modifierId: Integer. The creator or last modifier of the exam.
* dateModified: Date. The date when the user was created of last modified. Presented in ISO 8601 format. Inherited from schema.org/Article.
 

## Testing
There are five different test suites for testing five entities of the exam archive database API: user, teacher, archive, 
course and exam. Similarly, there are four test suites for testing 9 resources implemented in RESTful API: user, 
userlist, archive, archivelist, course, courselist, exam, examlist and examupload resources. 
Teacher resource is not part of the final implementation and thus, there are no unit tests for it. 
The tests can be run with following commands:

    export PYTHONPATH="$PYTHONPATH:./api"      # or in Windows: set PYTHONPATH=%PYTHONPATH%;./api
    
    # Run all the tests
    python test
    
    # Or run the tests one by one, starting from database test suite
    python -m test.database_api_test_archive
    python -m test.database_api_test_course
    python -m test.database_api_test_exam
    python -m test.database_api_test_user
    python -m test.database_api_test_teacher

    # RESTful API tests can be run one by one
    python -m test.rest_api_test_user
    python -m test.rest_api_test_archive
    python -m test.rest_api_test_course
    python -m test.rest_api_test_exam

