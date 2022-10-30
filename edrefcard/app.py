from flask import Flask, render_template

import data

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/list')
def bind_list():
    return render_template('bind_list.html')


@app.route('/binds/<bind>')
def bind_detail(bind):
    return render_template('bind_detail.html')


@app.route('/configs/<config>')
def configs(config):
    return 'Hello, World!'


@app.route('/devices')
def device_list():
    return render_template('device_list.html')


@app.route('/device/<device>')
def device_detail(device):
    return 'Hello, World!'


@app.context_processor
def bindings_data_context():
    return {
        'version': data.VERSION,
        'devices': data.SUPPORTED_DEVICES,
    }
