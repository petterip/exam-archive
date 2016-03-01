---------------------------------------------------
-- Create table statements                       --
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
	language_id INTEGER,
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
	language_id INTEGER,
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

COMMIT;
PRAGMA foreign_keys=ON;