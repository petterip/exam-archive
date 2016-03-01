# Run all test suites

import unittest, os
from database_api_test_archive import *
from database_api_test_course import *
from database_api_test_exam import *
from database_api_test_teacher import *
from database_api_test_user import *

from rest_api_test_user import *

# List of test suites
db_suites =  [unittest.TestLoader().loadTestsFromTestCase(ArchiveTestCase),
              unittest.TestLoader().loadTestsFromTestCase(CourseTestCase),
              unittest.TestLoader().loadTestsFromTestCase(ExamTestCase),
              unittest.TestLoader().loadTestsFromTestCase(TeacherTestCase),
              unittest.TestLoader().loadTestsFromTestCase(UserTestCase)]

rest_suites =  [unittest.TestLoader().loadTestsFromTestCase(RestUserTestCase)]

# Run each suite one by one
for suite in db_suites:
    unittest.TextTestRunner(verbosity=2).run(suite)

for suite in rest_suites:
    unittest.TextTestRunner(verbosity=2).run(suite)

