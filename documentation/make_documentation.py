# coding=UTF-8
#
# Generate documentation for following packages:
#    * exam_archive.py
#    * user_resource.py
#    * archive_resource.py
#    * course_resource.py
#    * exam_resource.py
#
# @authors: Ari Kairala, Petteri Ponsimaa

from functools import wraps
import os, re, pdoc
import exam_archive, user_resource, archive_resource, course_resource, exam_resource

# Define the folder where to save the generated documentation
DOC_FOLDER = 'documentation'

# Define the packages of which the documentation is generated
PACKAGES = [exam_archive, user_resource, archive_resource, course_resource, exam_resource]

# Define the extension to be used for output
HTML_EXTENSION = '.html'
TXT_EXTENSION = '.txt'

if __name__ == '__main__':
    print 'Saving documentation in plain text and html format to:'

    # During development let the source packages be found
    if os.path.exists('../documentation'):
        os.chdir("../")

    # Go through the packages one by one and same the documentation into files
    for doc_module in PACKAGES:
        doc = pdoc.Module(doc_module)
        html = doc.html()
        text = doc.text()

        # Pdoc is not perfect - clean up the output before writing it into a file
        html = re.sub(r"(<code>[0-9]+</code>[^<]+)",r"\1<br/>", html)

        # Save the documentation in HTML format.
        file_path = DOC_FOLDER + '/' + doc_module.__name__ + HTML_EXTENSION
        file = open(file_path, "w")
        file.write(html.encode('utf-8'))
        print file_path
        file.close()

        # Save the documentation in text format.
        file_path = DOC_FOLDER + '/' + doc_module.__name__ + TXT_EXTENSION
        file = open(file_path, "w")
        file.write(text.encode('utf-8'))
        print file_path
        file.close()

