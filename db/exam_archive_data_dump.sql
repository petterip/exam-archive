---------------------------------------------------
-- Create table statements and insert statements --
-- for Exam Archive                              --
--                                               --
-- Last updated: 26.2.2015                       --
---------------------------------------------------

PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

-- Create user table
CREATE TABLE IF NOT EXISTS user(
	user_id INTEGER PRIMARY KEY AUTOINCREMENT,
	user_type TEXT NOT NULL DEFAULT ‘basic’,
	username TEXT UNIQUE,
	password TEXT DEFAULT NULL,
	archive_id INTEGER,
	modifier_id TEXT,
	last_modified DATETIME DEFAULT CURRENT_TIMESTAMP,
	UNIQUE(username),

	FOREIGN KEY(archive_id) REFERENCES archive(archive_id) ON DELETE SET NULL,
	FOREIGN KEY(modifier_id) REFERENCES user(user_id) ON DELETE SET NULL
);

-- Create archive table
CREATE TABLE IF NOT EXISTS archive(
	archive_id INTEGER PRIMARY KEY AUTOINCREMENT,
	archive_name TEXT NOT NULL,
	organisation_name TEXT NOT NULL,
	identification_needed INTEGER DEFAULT '0',
	modifier_id INTEGER,
	last_modified DATETIME DEFAULT CURRENT_TIMESTAMP,

	FOREIGN KEY(modifier_id) REFERENCES user(user_id) ON DELETE SET NULL,
	UNIQUE(organisation_name, archive_name)
);

-- Create course table
CREATE TABLE IF NOT EXISTS course(
	course_id INTEGER PRIMARY KEY AUTOINCREMENT,
	archive_id INTEGER NOT NULL,
	course_code TEXT,
	course_name TEXT NOT NULL,
	description TEXT,
	teacher_id INTEGER,
	url TEXT,
	credit_points INTEGER,
	language_id TEXT,
	modifier_id TEXT,
	last_modified DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(archive_id, course_name, language_id)
	FOREIGN KEY(archive_id) REFERENCES archive(archive_id) ON DELETE CASCADE,
	FOREIGN KEY(teacher_id) REFERENCES teacher(teacher_id) ON DELETE SET NULL,
	FOREIGN KEY(language_id) REFERENCES language(language_id) ON DELETE SET NULL,
	FOREIGN KEY(modifier_id) REFERENCES user(user_id) ON DELETE SET NULL
);

-- Create exam table
CREATE TABLE IF NOT EXISTS exam(
	exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
	course_id INTEGER NOT NULL,
	examiner_id INTEGER,
	date TEXT,
	file_attachment INTEGER,
	language_id TEXT,
	modifier_id TEXT,
	last_modified DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(exam_id, course_id, language_id)
	FOREIGN KEY(course_id) REFERENCES course(course_id) ON DELETE CASCADE,
	FOREIGN KEY(examiner_id) REFERENCES teacher(teacher_id) ON DELETE SET NULL,
	FOREIGN KEY(language_id) REFERENCES language(language_id) ON DELETE SET NULL,
	FOREIGN KEY(modifier_id) REFERENCES user(user_id)
);

-- Create teacher table
CREATE TABLE IF NOT EXISTS teacher(
	teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,
	first_name TEXT NOT NULL,
	last_name TEXT NOT NULL,
	office TEXT,
	street_address TEXT,
	postal_code TEXT,
	city TEXT,
	phone TEXT,
	email TEXT,
	other_info TEXT,
	modifier_id TEXT,
	last_modified DATETIME DEFAULT CURRENT_TIMESTAMP,

	FOREIGN KEY(modifier_id) REFERENCES user(user_id) ON DELETE SET NULL
);

-- Create language table
CREATE TABLE IF NOT EXISTS language(
	language_id TEXT PRIMARY KEY,
	language_name TEXT NOT NULL
);

-- Populating the database with some test information
--
-- Insert some test users
INSERT INTO "user" VALUES(1,'super','bigboss','421c11091311963998d4c1c1b77d53b36967e9d111bec0f9760f7812dd151f88',1,NULL,'2015-02-25');
INSERT INTO "user" VALUES(2,'admin','antti.admin','17f80754644d33ac685b0842a402229adbb43fc9312f7bdf36ba24237a1f1ffb',1,1,'2015-02-25');
INSERT INTO "user" VALUES(3,'basic','testuser','ae5deb822e0d71992900471a7199d0d95b8e7c9d05c40a8245a281fd2c1d6684',1,1,'2015-02-25');
--
-- Create test archive
INSERT INTO "archive" VALUES(1,'Information Processing Science','Blanko',1,1,'2015-02-26');
INSERT INTO "archive" VALUES(2,'Wireless Communications Engineering','OTiT',1,1,'2015-03-03');
INSERT INTO "archive" VALUES(3,'Electrical Engineering','SIK',1,1,'2015-03-03');
--
-- Insert couple test courses
INSERT INTO "course" VALUES(1,1,'810136P','Johdatus tietojenkäsittelytieteisiin','Lorem ipsum','1','http://weboodi.oulu.fi/',4,'fi',1,'2015-02-26');
INSERT INTO "course" VALUES(2,1,'812671S','Usability Testing','Lorem ipsum','1','http://weboodi.oulu.fi/',5,'en',1,'2015-02-26');
INSERT INTO "course" VALUES(3,1,'815660S','Software Engineering Management Measurement and Improvement','Lorem ipsum','1','http://weboodi.oulu.fi/',5,'en',1,'2015-03-03');
--
-- Insert exams for test courses
INSERT INTO "exam" VALUES(1,1,2,'2013-02-21','810136P_exam01.pdf','fi',1,'2015-02-26');
INSERT INTO "exam" VALUES(2,1,2,'2014-02-28','810136P_exam02.pdf','fi',1,'2015-02-26');
INSERT INTO "exam" VALUES(3,1,2,'2015-05-05','810136P_exam03.pdf','fi',1,'2015-03-03');
INSERT INTO "exam" VALUES(4,2,2,'2013-02-21','812671S_exam01.pdf','en',1,'2015-02-26');
INSERT INTO "exam" VALUES(5,3,2,'2015-02-28','810136P_exam02.pdf','fi',1,'2015-02-26');

--
-- Insert test teacher and his assistant
INSERT INTO "teacher" VALUES(1,'Tero','Testaaja','TOL301','Testiosoite 123','90500','OULU','+358401231231','tero.testaaja@oulu.fi',NULL,1,'2015-02-26');
INSERT INTO "teacher" VALUES(2,'Terhi','Testi','TOL301','Testikuja 12 A 1','90500','OULU','+358404564566','terhi.testi@oulu.fi',NULL,1,'2015-02-26');
--
-- Define languages
INSERT INTO "language" VALUES('fi','Finnish');
INSERT INTO "language" VALUES('sv','Swedish');
INSERT INTO "language" VALUES('en','English');

COMMIT;
PRAGMA foreign_keys=ON;
