from flask import Flask
#Define the application and the api
app = Flask(__name__, static_folder='ui', static_url_path='')
app.debug=True
