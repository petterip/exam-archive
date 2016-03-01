# coding=UTF-8
#
# Runs the application bu starting first RESTful API and then web client,
# which demonstrates how the API can be used.
#
# @authors: Ari Kairala, Petteri Ponsimaa
# The class is based on code made by Ivan Sanchez (from exercise 4 code of run.py).

from api.server import app as server
from client.application import app as client
from werkzeug.serving import run_simple
from werkzeug.wsgi import DispatcherMiddleware
from flask import Flask

application = DispatcherMiddleware(server, {
     '/client': client
})
if __name__ == '__main__':
    run_simple('localhost', 8080, application,
               use_reloader=True, use_debugger=True, use_evalex=True)

