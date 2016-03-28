from flask import Flask
app = Flask(__name__)
app.secret_key = 'set the secret key. Keep this really secret'

import oauth
