import re

from flask import Flask, render_template, request, send_from_directory

import data
from bindings import ConfigFactory

app = Flask(__name__)
config = ConfigFactory(app)
config.initialize_blank_device_images()


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


@app.route('/configs/<path:path>')
def configs(path):
    return send_from_directory('configs', path)


@app.route('/devices')
def device_list():
    return render_template('device_list.html')


@app.route('/device/<device>')
def device_detail(device):
    if device not in data.SUPPORTED_DEVICES:
        #errors = f'<h1>{device} is not a supported controller.</h1>'
        ...
    return render_template('device_detail.html', name=data.SUPPORTED_DEVICES[device]["Template"], warnings={})


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


@app.template_filter('config_path')
def config_path_filter(image, name):
    if '::' in image:
        m = re.search(r'(.*)::([01])', image)
        device = m.group(1)
        idx = int(m.group(2))
    else:
        device = image
        idx = 0

    path = f'../configs/{name[:2]}/{name}-{data.SUPPORTED_DEVICES[device]["Template"]}'
    if idx != 0:
        path += f'-{idx}'
    return f'{path}.jpg'
