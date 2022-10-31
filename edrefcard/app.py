from flask import Flask, render_template, request

import data
from bindings import ConfigFactory

app = Flask(__name__)
config = ConfigFactory(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/list')
def bind_list():
    def has_device(bind, devices):
        bind_devices = [key.split('::')[0] for key in bind['devices']]
        return any(device in bind_devices for device in devices)

    binds = config.all(sort_key=lambda obj: str(obj['description']).casefold())
    device_filter = set(request.args.getlist("deviceFilter"))
    if device_filter:
        valid_devices = [
            device
            for controller in device_filter
            for device in data.SUPPORTED_DEVICES.get(controller, {}).get('HandledDevices', [])
        ]
        binds = [bind for bind in binds if has_device(bind, valid_devices)]
    return render_template('bind_list.html', binds=binds)


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


@app.template_filter('bind_controllers')
def bind_controllers_filter(devices):
    return {
        data.HOTAS_DETAILS.get(controller, dict()).get('displayName', controller)
        for controller in [key.split('::')[0] for key in devices]
        if controller not in ['Mouse', 'Keyboard']
    }
