#!/usr/bin/env python3

from flask import Flask
from lxml import etree

from collections import OrderedDict

from wand.drawing import Drawing
from wand.image import Image
from wand.font import Font
from wand.color import Color

import string
import random
import datetime
import codecs
import os
import pickle
from pathlib import Path
from urllib.parse import urljoin

from data import SUPPORTED_DEVICES, HOTAS_DETAILS
from utils import layout_text


class ConfigFactory:
    GROUP_STYLES = {
        'General': ('Black', 'Regular', 'Normal'),
        'Misc': ('Black', 'Regular', 'Normal'),
        'Modifier': ('Black', 'Bold', 'Normal'),
        'Galaxy map': ('ForestGreen', 'Regular', 'Normal'),
        'Holo-Me': ('Sienna', 'Regular', 'Normal'),
        'Multicrew': ('SteelBlue', 'Bold', 'Normal'),
        'Fighter': ('DarkSlateBlue', 'Regular', 'Normal'),
        'Camera': ('OliveDrab', 'Regular', 'Normal'),
        'Head look': ('IndianRed', 'Regular', 'Normal'),
        'Ship': ('Crimson', 'Regular', 'Normal'),
        'SRV': ('MediumPurple', 'Regular', 'Normal'),
        'Scanners': ('DarkOrchid', 'Regular', 'Normal'),
        'UI': ('DarkOrange', 'Regular', 'Normal'),
        'OnFoot': ('CornflowerBlue', 'Regular', 'Normal'),
    }
    CATEGORY_STYLES = {
        'General': ('DarkSlateBlue', 'Regular', 'Normal'),
        'Combat': ('Crimson', 'Regular', 'Normal'),
        'Social': ('ForestGreen', 'Regular', 'Normal'),
        'Navigation': ('Black', 'Regular', 'Normal'),
        'UI': ('DarkOrange', 'Regular', 'Normal'),
    }
    MODIFIER_STYLES = [
        ('Black', 'Regular', 'Normal'),
        ('Crimson', 'Regular', 'Normal'),
        ('ForestGreen', 'Regular', 'Normal'),
        ('DarkSlateBlue', 'Regular', 'Normal'),
        ('DarkOrange', 'Regular', 'Normal'),
        ('DarkOrchid', 'Regular', 'Normal'),
        ('SteelBlue', 'Regular', 'Normal'),
        ('Sienna', 'Regular', 'Normal'),
        ('IndianRed', 'Regular', 'Normal'),
        ('CornflowerBlue', 'Regular', 'Normal'),
        ('OliveDrab', 'Regular', 'Normal'),
        ('MediumPurple', 'Regular', 'Normal'),
        ('DarkSalmon', 'Regular', 'Normal'),
        ('LightSlateGray', 'Regular', 'Normal'),
    ]

    def __init__(self, app: Flask):
        self.app = app

    def create(self, name: str):
        if not name:
            raise ValueError('Config must have a name')
        return Config(self, name)

    def create_random(self):
        def new_name():
            return ''.join(random.choice(string.ascii_lowercase) for x in range(6))

        config = Config(self, new_name())
        while config.path.exists():
            config = Config(self, new_name())
        return config

    @property
    def root_path(self):
        return Path(self.app.root_path) / 'configs'

    @property
    def template_path(self):
        return Path(self.app.root_path) / 'res'

    def font_path(self, weight: str, style: str):
        if style == 'Normal':
            style = ''
        if weight == 'Regular' and style != '':
            weight = ''
        return str(Path(self.app.root_path) / 'static' / f'fonts/Exo2.0-{weight}{style}.otf')

    def group_style(self, name: str):
        color, font_weight, font_style = self.GROUP_STYLES[name]
        return {'Color': Color(color), 'Font': self.font_path(font_weight, font_style)}

    def category_style(self, name: str):
        color, font_weight, font_style = self.CATEGORY_STYLES[name]
        return {'Color': Color(color), 'Font': self.font_path(font_weight, font_style)}

    def modifier_style(self, i: int):
        color, font_weight, font_style = self.MODIFIER_STYLES[i % len(self.MODIFIER_STYLES)]
        return {'Color': Color(color), 'Font': self.font_path(font_weight, font_style)}

    def all(self, sort_key=None):
        def unpickle(path) -> Config:
            with path.open('rb') as file:
                config = pickle.load(file)
                config['runID'] = path.stem
            return config

        objs = [unpickle(path) for path in self.root_path.glob('**/*.replay')]
        objs.sort(key=sort_key)
        return objs

    def initialize_blank_device_images(self):
        for key, device in SUPPORTED_DEVICES.items():
            if key == 'Keyboard':
                continue
            config = self.create(device['Template'])
            output_path = config.path.with_suffix('.jpg')
            if output_path.exists():
                continue

            with Image(filename=self.template_path / f'{device["Template"]}.svg') as output:
                with Drawing() as context:
                    context.font = self.font_path('Regular', 'Normal')
                    context.text_antialias = True
                    context.font_style = 'normal'

                    for key_device in device.get('KeyDevices', device.get('HandledDevices')):
                        for keycode, box in HOTAS_DETAILS[key_device].items():
                            if keycode == 'displayName':
                                continue
                            context.stroke_width = 1
                            context.stroke_color = Color('Red')
                            context.fill_color = Color('LightGreen')
                            context.rectangle(top=box['y'], left=box['x'], width=box['width'],
                                              height=box.get('height', 54))
                            context.stroke_width = 0
                            context.fill_color = Color('Black')
                            source_texts = [{'Text': keycode, 'Group': 'General', 'Style': self.group_style('General')}]
                            texts = layout_text(output, context, source_texts, box, 40)
                            for text in texts:
                                context.font_size = text['Size']
                                # TODO dry this up
                                context.font = text['Style']['Font']
                                context.text(x=text['X'], y=text['Y'], body=text['Text'])
                    config.mkdir()
                    context.draw(output)
                    output.save(filename=str(output_path))


class Config:
    @staticmethod
    def web_root():
        return urljoin(os.environ.get('SCRIPT_URI', 'https://edrefcard.info/'), '/')

    def __init__(self, factory: ConfigFactory, name: str):
        self.factory = factory
        self.name = name

    def __repr__(self):
        return f"Config('{self.name}')"

    @property
    def path(self):
        return self.factory.root_path / self.name[:2] / self.name

    def pathWithNameAndSuffix(self, name, suffix):
        return self.path.with_name(f'{self.name}-{name}').with_suffix(suffix)

    def mkdir(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def bindsURL(self):
        return urljoin(Config.web_root(), f"configs/{self.name}.binds")

# Output section

def writeUrlToDrawing(config, drawing, public):
    url = config.refcardURL() if public else Config.web_root()
    drawing.push()
    drawing.font = getFontPath('SemiBold', 'Normal')
    drawing.font_size = 72
    drawing.text(x=23, y=252, body=url)
    drawing.pop()


# Create a keyboard image from the template plus bindings
def createKeyboardImage(physicalKeys, modifiers, source, imageDevices, biggestFontSize, displayGroups, runId, public):
    config = Config(runId)
    filePath = config.pathWithNameAndSuffix(source, '.svg')

    # See if it already exists or if we need to recreate it
    if filePath.exists():
        return True
    with Image(filename='../res/' + source + '.svg') as sourceImg:
        with Drawing() as context:

            # Defaults for the font
            context.font = getFontPath('Regular', 'Normal')
            context.text_antialias = True
            context.font_style = 'normal'
            context.stroke_width = 0
            context.fill_color = Color('Black')
            context.fill_opacity = 1

            # Add the ID to the title
            writeUrlToDrawing(config, context, public)

            outputs = {}
            for group in displayGroups:
                outputs[group] = {}

            # Find the correct bindings and order them appropriately
            for physicalKeySpec, physicalKey in physicalKeys.items():
                itemDevice = physicalKey.get('Device')
                itemKey = physicalKey.get('Key')

                # Only show it if we are handling the appropriate image at this time
                if itemDevice not in imageDevices:
                    continue

                for modifier, bind in physicalKey.get('Binds').items():
                    for controlKey, control in bind.get('Controls').items():
                        bind = {'Control': control, 'Key': itemKey, 'Modifiers': []}

                        if modifier != 'Unmodified':
                            for modifierKey, modifierControls in modifiers.items():
                                for modifierControl in modifierControls:
                                    if modifierControl.get('ModifierKey') == modifier and modifierControl.get(
                                            'Key') is not None:
                                        bind['Modifiers'].append(modifierControl.get('Key'))

                        outputs[control['Group']][control['Name']] = bind

            # Set up a screen state to handle output
            screenState = {'baseX': 60, 'baseY': 320, 'maxWidth': 0, 'thisWidth': 0}
            screenState['currentX'] = screenState['baseX']
            screenState['currentY'] = screenState['baseY']

            font = Font(getFontPath('Regular', 'Normal'), antialias=True, size=biggestFontSize)
            groupTitleFont = Font(getFontPath('Regular', 'Normal'), antialias=True, size=biggestFontSize * 2)
            context.stroke_width = 2
            context.stroke_color = Color('Black')
            context.fill_opacity = 0

            # Go through once for each display group
            for displayGroup in displayGroups:
                if outputs[displayGroup] == {}:
                    continue

                writeText(context, sourceImg, displayGroup, screenState, groupTitleFont, False, True)

                orderedOutputs = OrderedDict(
                    sorted(outputs[displayGroup].items(), key=lambda x: x[1].get('Control').get('Order')))
                for bindKey, bind in orderedOutputs.items():
                    for modifier in bind.get('Modifiers', []):
                        writeText(context, sourceImg, transKey(modifier), screenState, font, True, False)
                    writeText(context, sourceImg, transKey(bind.get('Key')), screenState, font, True, False)
                    writeText(context, sourceImg, bind.get('Control').get('Name'), screenState, font, False, True)

            context.draw(sourceImg)
            sourceImg.save(filename=str(filePath))
    return True


def appendKeyboardImage(createdImages, physicalKeys, modifiers, displayGroups, runId, public):
    def countKeyboardItems(physicalKeys):
        keyboardItems = 0
        for physicalKey in physicalKeys.values():
            if physicalKey.get('Device') == 'Keyboard':
                for bind in physicalKey.get('Binds').values():
                    keyboardItems = keyboardItems + len(bind.get('Controls'))
        return keyboardItems

    def fontSizeForKeyBoardItems(physicalKeys):
        keyboardItems = countKeyboardItems(physicalKeys)
        if keyboardItems > 48:
            fontSize = 40 - int(((keyboardItems - 48) / 20) * 4)
            if fontSize < 24:
                fontSize = 24
        else:
            fontSize = 40
        return fontSize

    fontSize = fontSizeForKeyBoardItems(physicalKeys)
    createKeyboardImage(physicalKeys, modifiers, 'keyboard', ['Keyboard'], fontSize, displayGroups, runId, public)
    createdImages.append('Keyboard')


# Write text, possible wrapping
def writeText(context, img, text, screenState, font, surround, newLine):
    border = 4

    # Work out the size of the text
    context.font = font.path
    context.font_style = 'normal'
    context.font_size = font.size
    context.push()
    context.stroke_width = 0
    context.fill_color = Color('Black')
    context.fill_opacity = 1

    if text is None or text == '':
        text = 'invalid'
        context.fill_color = Color('Red')

    metrics = context.get_font_metrics(img, text, multiline=False)
    if screenState['currentY'] + int(metrics.text_height + 32) > 2160:
        # Gone off the bottom of the page; go to next column
        screenState['currentY'] = screenState['baseY']
        screenState['baseX'] = screenState['baseX'] + screenState['maxWidth'] + 49
        screenState['currentX'] = screenState['baseX']
        screenState['maxWidth'] = 0
        screenState['thisWidth'] = 0
    # Center the text
    x = screenState['currentX']
    y = screenState['currentY'] + int(metrics.ascender)
    context.text(x=x, y=y, body=text)
    context.pop()

    if surround is True:
        # text y is baseline, rectangle y is top
        y = screenState['currentY'] - border
        context.rectangle(left=x - (border * 4), top=y - (border * 2), width=int(metrics.text_width) + (border * 8),
                          height=int(metrics.text_height) + (border * 4), radius=30)
        width = int(metrics.text_width + 48)
    else:
        width = int((metrics.text_width + 72) / 48) * 48
    screenState['thisWidth'] = screenState['thisWidth'] + width

    if newLine is True:
        if screenState['thisWidth'] > screenState['maxWidth']:
            screenState['maxWidth'] = screenState['thisWidth']
        screenState['currentY'] = screenState['currentY'] + int(metrics.text_height + 32)
        screenState['currentX'] = screenState['baseX']
        screenState['thisWidth'] = 0
    else:
        screenState['currentX'] = screenState['currentX'] + width


# Return whether a binding is a redundant specialisation and thus can be hidden
def isRedundantSpecialisation(control, bind):
    moreGeneralControls = control.get('HideIfSameAs')
    if len(moreGeneralControls) == 0:
        return False
    for moreGeneralMatch in bind.get('Controls').keys():
        if moreGeneralMatch in moreGeneralControls:
            return True
    return False


# Create a HOTAS image from the template plus bindings
def createHOTASImage(physicalKeys, modifiers, source, imageDevices, biggestFontSize, config, public, styling,
                     deviceIndex, misconfigurationWarnings):
    # Set up the path for our file
    runId = config.name
    if deviceIndex == 0:
        name = source
    else:
        name = f'{source}-{deviceIndex}'
    filePath = config.pathWithNameAndSuffix(name, '.svg')

    # See if it already exists or if we need to recreate it
    if filePath.exists():
        return True
    with Image(filename='../res/' + source + '.svg') as sourceImg:
        with Drawing() as context:

            # Defaults for the font
            context.font = getFontPath('Regular', 'Normal')
            context.text_antialias = True
            context.font_style = 'normal'
            context.stroke_width = 0
            context.fill_color = Color('Black')
            context.fill_opacity = 1

            # Add the ID to the title
            writeUrlToDrawing(config, context, public)

            for physicalKeySpec, physicalKey in physicalKeys.items():
                itemDevice = physicalKey.get('Device')
                itemDeviceIndex = int(physicalKey.get('DeviceIndex'))
                itemKey = physicalKey.get('Key')

                # Only show it if we are handling the appropriate image at this time
                if itemDevice not in imageDevices:
                    continue

                # Only show it if we are handling the appropriate index at this time
                if itemDeviceIndex != deviceIndex:
                    continue

                # Find the details for the control
                texts = []
                try:
                    hotasDetail = HOTAS_DETAILS.get(itemDevice).get(itemKey)
                except AttributeError:
                    hotasDetail = None
                if hotasDetail is None:
                    logError(f'{runId}: No drawing box found for {physicalKeySpec}\n')
                    continue

                # First obtain the modifiers if there are any
                for keyModifier in modifiers.get(physicalKeySpec, []):
                    if styling == 'Modifier':
                        style = ModifierStyles.index(keyModifier.get('Number'))
                    else:
                        style = groupStyles.get('Modifier')
                    texts.append(
                        {'Text': f'Modifier {keyModifier.get("Number")}', 'Group': 'Modifier', 'Style': style})
                if '::Joy' in physicalKeySpec:
                    # Same again but for positive modifier
                    for keyModifier in modifiers.get(physicalKeySpec.replace('::Joy', '::Pos_Joy'), []):
                        if styling == 'Modifier':
                            style = ModifierStyles.index(keyModifier.get('Number'))
                        else:
                            style = groupStyles.get('Modifier')
                        texts.append(
                            {'Text': f'Modifier {keyModifier.get("Number")}', 'Group': 'Modifier', 'Style': style})
                    # Same again but for negative modifier
                    for keyModifier in modifiers.get(physicalKeySpec.replace('::Joy', '::Neg_Joy'), []):
                        if styling == 'Modifier':
                            style = ModifierStyles.index(keyModifier.get('Number'))
                        else:
                            style = groupStyles.get('Modifier')
                        texts.append(
                            {'Text': f'Modifier {keyModifier.get("Number")}', 'Group': 'Modifier', 'Style': style})

                # Next obtain unmodified bindings
                for modifier, bind in physicalKey.get('Binds').items():
                    if modifier == 'Unmodified':
                        for controlKey, control in bind.get('Controls').items():
                            if isRedundantSpecialisation(control, bind):
                                continue
                            # Check if this is a digital control on an analogue stick with an analogue equivalent
                            if control.get('Type') == 'Digital' and control.get(
                                    'HasAnalogue') is True and hotasDetail.get('Type') == 'Analogue':
                                if misconfigurationWarnings == '':
                                    misconfigurationWarnings = \
                                        '<h1>Misconfiguration detected</h1>You have one or more analogue controls ' \
                                        'configured incorrectly. Please see <a ' \
                                        'href="https://forums.frontier.co.uk/showthread.php?t=209792">this thread</a> ' \
                                        'for details of the problem and how to correct it.<br/> <b>Your misconfigured ' \
                                        f'controls:</b> <b>{control["Name"]}</b> '
                                else:
                                    misconfigurationWarnings = f'{misconfigurationWarnings}, <b>{control["Name"]}</b>'
                                # logError('%s: Digital command %s found on hotas control %s::%s\n' % (runId, control['Name'], itemDevice, itemKey))

                            if styling == 'Modifier':
                                texts.append({'Text': f'{control.get("Name")}', 'Group': control.get('Group'),
                                              'Style': ModifierStyles.index(0)})
                            elif styling == 'Category':
                                texts.append({'Text': f'{control.get("Name")}', 'Group': control.get('Group'),
                                              'Style': categoryStyles.get(control.get('Category', 'General'))})
                            else:
                                texts.append({'Text': f'{control.get("Name")}', 'Group': control.get('Group'),
                                              'Style': groupStyles.get(control.get('Group'))})

                # Next obtain bindings with modifiers
                # Lazy approach to do this but covers us for now
                for curModifierNum in range(1, 200):
                    for modifier, bind in physicalKey.get('Binds').items():
                        if modifier != 'Unmodified':
                            keyModifiers = modifiers.get(modifier)
                            modifierNum = 0
                            for keyModifier in keyModifiers:
                                if keyModifier['ModifierKey'] == modifier:
                                    modifierNum = keyModifier['Number']
                                    break
                            if modifierNum != curModifierNum:
                                continue
                            for controlKey, control in bind.get('Controls').items():
                                if isRedundantSpecialisation(control, bind):
                                    continue
                                if styling == 'Modifier':
                                    texts.append({'Text': f'{control.get("Name")}', control.get('Group'): 'Modifier',
                                                  'Style': ModifierStyles.index(curModifierNum)})
                                elif styling == 'Category':
                                    texts.append({'Text': f'{control.get("Name")}[{curModifierNum}]',
                                                  'Group': control.get('Group'),
                                                  'Style': categoryStyles.get(control.get('Category', 'General'))})
                                else:
                                    texts.append({'Text': f'{control.get("Name")}[{curModifierNum}]',
                                                  'Group': control.get('Group'),
                                                  'Style': groupStyles.get(control.get('Group'))})

                # Obtain the layout of the texts and write them
                texts = layoutText(sourceImg, context, texts, hotasDetail, biggestFontSize)
                for text in texts:
                    context.font_size = text['Size']
                    context.font = text['Style']['Font']
                    if styling != 'None':
                        context.fill_color = text['Style']['Color']
                    context.text(x=text['X'], y=text['Y'], body=text['Text'])

            # Also need to add standalone modifiers (those without other binds)
            for modifierSpec, keyModifiers in modifiers.items():
                modifierTexts = []
                for keyModifier in keyModifiers:
                    if keyModifier.get('Device') not in imageDevices:
                        # We don't have an image for this device
                        continue
                    if int(keyModifier.get('DeviceIndex')) != deviceIndex:
                        # This is not four our current device
                        continue
                    if '/' in modifierSpec:
                        # This is a logical modifier so ignore it
                        continue
                    if physicalKeys.get(modifierSpec) is not None or physicalKeys.get(
                            modifierSpec.replace('::Pos_Joy', '::Joy')) is not None or physicalKeys.get(
                        modifierSpec.replace('::Neg_Joy', '::Joy')) is not None:
                        # This has already been handled because it has other binds
                        continue

                    modifierKey = keyModifier.get('Key')
                    hotasDetail = HOTAS_DETAILS.get(keyModifier.get('Device')).get(modifierKey)
                    if hotasDetail is None:
                        logError(f'{runId}: No location for {modifierSpec}\n')
                        continue

                    if styling == 'Modifier':
                        style = ModifierStyles.index(keyModifier.get('Number'))
                    else:
                        style = groupStyles.get('Modifier')
                    modifierTexts.append(
                        {'Text': f'Modifier {keyModifier.get("Number")}', 'Group': 'Modifier', 'Style': style})

                if modifierTexts != []:
                    # Obtain the layout of the modifier text and write it
                    modifierTexts = layoutText(sourceImg, context, modifierTexts, hotasDetail, biggestFontSize)
                    for text in modifierTexts:
                        context.font_size = text['Size']
                        context.font = text['Style']['Font']
                        if styling != 'None':
                            context.fill_color = text['Style']['Color']
                        context.text(x=text['X'], y=text['Y'], body=text['Text'])

            context.draw(sourceImg)
            sourceImg.save(filename=str(filePath))
    return True


# Parser section

def parseBindings(runId, xml, displayGroups, errors):
    parser = etree.XMLParser(encoding='utf-8', resolve_entities=False)
    try:
        tree = etree.fromstring(bytes(xml, 'utf-8'), parser=parser)
    except SyntaxError as e:
        errors.errors = f'''<h3>There was a problem parsing the file you supplied.</h3>
        <p>{e}</p>
        <p>Possibly you submitted the wrong file, or hand-edited it and made a mistake.</p>'''
        xml = '<root></root>'
        tree = etree.fromstring(bytes(xml, 'utf-8'), parser=parser)

    physicalKeys = {}
    modifiers = {}
    hotasModifierNum = 1
    keyboardModifierNum = 101
    devices = {}

    hasT16000MThrottle = len(tree.findall(".//*[@Device='T16000MTHROTTLE']")) > 0

    xmlBindings = tree.findall(".//Binding") + tree.findall(".//Primary") + tree.findall(".//Secondary")
    for xmlBinding in xmlBindings:
        controlName = xmlBinding.getparent().tag

        device = xmlBinding.get('Device')
        if device == '{NoDevice}':
            continue

        # Rewrite the device if this is a T16000M stick and we have a T16000M throttle
        if device == 'T16000M' and hasT16000MThrottle:
            device = 'T16000MFCS'

        deviceIndex = xmlBinding.get('DeviceIndex', 0)

        key = xmlBinding.get('Key')
        # Remove the Neg_ and Pos_ headers to put digital buttons on analogue devices
        if key is not None:
            if key.startswith('Neg_'):
                key = key.replace('Neg_', '', 1)
            if key.startswith('Pos_'):
                key = key.replace('Pos_', '', 1)

        def modifierSortKey(modifierInfo):
            modifierDevice = modifierInfo.get('Device')
            # Rewrite the device if this is a T16000M stick and we have a T16000M throttle
            if modifierDevice == 'T16000M' and hasT16000MThrottle == True:
                modifierDevice = 'T16000MFCS'
            modifierKey = f'{modifierDevice}::{modifierInfo.get("DeviceIndex", 0)}::{modifierInfo.get("Key")}'
            return modifierKey

        modifiersInfo = xmlBinding.findall('Modifier')
        modifiersInfo = sorted(modifiersInfo, key=modifierSortKey)
        modifiersKey = 'Unmodified'
        if modifiersInfo:
            modifiersKey = ''
            for modifierInfo in modifiersInfo:
                modifierKey = modifierSortKey(modifierInfo)
                if modifiersKey == '':
                    modifiersKey = modifierKey
                else:
                    modifiersKey = f'{modifiersKey}/{modifierKey}'
            # See if we already have the modifier
            foundKeyModifier = False
            keyModifiers = modifiers.get(modifiersKey, [])
            # Store it in case it didn't exist prior to the above call
            modifiers[modifiersKey] = keyModifiers
            for keyModifier in keyModifiers:
                if keyModifier.get('ModifierKey') == modifiersKey:
                    foundKeyModifier = True
                    break
            if not foundKeyModifier:
                # Create individual modifiers
                for modifierInfo in modifiersInfo:
                    modifier = {'ModifierKey': modifiersKey}
                    modifierDevice = modifierInfo.get('Device')
                    # Rewrite the device if this is a T16000M stick and we have a T16000M throttle
                    if modifierDevice == 'T16000M' and hasT16000MThrottle:
                        modifierDevice = 'T16000MFCS'
                    if modifierDevice == 'Keyboard':
                        modifier['Number'] = keyboardModifierNum
                    else:
                        modifier['Number'] = hotasModifierNum
                    modifier['Device'] = modifierDevice
                    modifier['DeviceIndex'] = modifierInfo.get('DeviceIndex', 0)
                    modifier['Key'] = modifierInfo.get('Key')
                    modifierKey = f'{modifierDevice}::{modifierInfo.get("DeviceIndex", 0)}::{modifierInfo.get("Key")}'
                    updatedModifiers = modifiers.get(modifierKey, [])
                    updatedModifiers.append(modifier)
                    modifiers[modifierKey] = updatedModifiers
                if '/' in modifiersKey:
                    # Also need to add composite modifier
                    modifier = {'ModifierKey': modifiersKey}
                    modifierDevice = modifierInfo.get('Device')
                    # Rewrite the device if this is a T16000M stick and we have a T16000M throttle
                    if modifierDevice == 'T16000M' and hasT16000MThrottle == True:
                        modifierDevice = 'T16000MFCS'
                    if modifierDevice == 'Keyboard':
                        modifier['Number'] = keyboardModifierNum
                    else:
                        modifier['Number'] = hotasModifierNum
                    keyModifiers.append(modifier)
                if modifierInfo.get('Device') == 'Keyboard':
                    keyboardModifierNum = keyboardModifierNum + 1
                else:
                    hotasModifierNum = hotasModifierNum + 1
        control = controls.get(controlName)
        if control is None:
            logError(f'{runId}: No control for {controlName}\n')
            control = {'Group': 'General', 'Name': controlName, 'Order': 999, 'HideIfSameAs': [], 'Type': 'Digital'}
        if control['Group'] not in displayGroups:
            # The user isn't interested in this control group so drop it
            continue

        itemKey = f'{device}::{deviceIndex}::{key}'
        deviceKey = f'{device}::{deviceIndex}'
        # Obtain the relevant supported device
        thisDevice = None
        for supportedDevice in SUPPORTED_DEVICES.values():
            if device in supportedDevice['HandledDevices']:
                thisDevice = supportedDevice
                break
        devices[deviceKey] = thisDevice
        physicalKey = physicalKeys.get(itemKey)
        if physicalKey is None:
            physicalKey = {'Device': device, 'DeviceIndex': deviceIndex, 'Binds': {},
                           # Get the unaltered key (might be prefixed with Neg_ or Pos_) and the mapped key
                           'BaseKey': xmlBinding.get('Key'), 'Key': key}
            physicalKeys[itemKey] = physicalKey
        bind = physicalKey['Binds'].get(modifiersKey)
        if bind is None:
            bind = {'Controls': OrderedDict()}
            physicalKey['Binds'][modifiersKey] = bind
        bind['Controls'][controlName] = control

    return physicalKeys, modifiers, devices


def parseForm(form):
    displayGroups = []
    if form.getvalue('showgalaxymap'):
        displayGroups.append('Galaxy map')
    if form.getvalue('showheadlook'):
        displayGroups.append('Head look')
    if form.getvalue('showsrv'):
        displayGroups.append('SRV')
    if form.getvalue('showscanners'):
        displayGroups.append('Scanners')
    if form.getvalue('showship'):
        displayGroups.append('Ship')
    if form.getvalue('showui'):
        displayGroups.append('UI')
    if form.getvalue('showfighter'):
        displayGroups.append('Fighter')
    if form.getvalue('showonfoot'):
        displayGroups.append('OnFoot')
    if form.getvalue('showmulticrew'):
        displayGroups.append('Multicrew')
    if form.getvalue('showcamera'):
        displayGroups.append('Camera')
    if form.getvalue('showcommandercreator'):
        displayGroups.append('Holo-Me')
    if form.getvalue('showmisc'):
        displayGroups.append('Misc')

    styling = 'None'  # Yes we do mean a string 'None'
    if form.getvalue('styling') == 'group':
        styling = 'Group'
    if form.getvalue('styling') == 'category':
        styling = 'Category'
    if form.getvalue('styling') == 'modifier':
        styling = 'Modifier'
    description = form.getvalue('description')
    if description is None:
        description = ''
    return displayGroups, styling, description


def saveReplayInfo(config, description, styling, displayGroups, devices, errors):
    replayInfo = {'displayGroups': displayGroups, 'misconfigurationWarnings': errors.misconfigurationWarnings,
                  'unhandledDevicesWarnings': errors.unhandledDevicesWarnings, 'deviceWarnings': errors.deviceWarnings,
                  'styling': styling, 'description': description,
                  'timestamp': datetime.datetime.now(datetime.timezone.utc), 'devices': devices}
    replayPath = config.path.with_suffix('.replay')
    with replayPath.open('wb') as pickleFile:
        pickle.dump(replayInfo, pickleFile)


def parseLocalFile(filePath):
    displayGroups = groupStyles.keys()
    config = Config('000000')
    errors = Errors()
    with filePath.open() as f:
        xml = f.read()
        (physicalKeys, modifiers, devices) = parseBindings(config.name, xml, displayGroups, errors)
        return (physicalKeys, modifiers, devices), errors


# API section

def processForm(form):
    config = Config.new_random()
    styling = 'None'
    description = ''
    options = {}
    public = False
    createdImages = []
    errors = Errors()

    deviceForBlockImage = form.getvalue('blocks')
    mode = determineMode(form)
    if mode is Mode.invalid:
        errors.errors = 'That is not a valid description. Leading punctuation is not allowed.</h1>'
        xml = '<root></root>'
    elif mode is Mode.blocks:
        try:
            deviceForBlockImage = form.getvalue('blocks')
            createBlockImage(deviceForBlockImage)
        except KeyError:
            errors.errors = f'<h1>{deviceForBlockImage} is not a supported controller.</h1>'
            xml = '<root></root>'
        createdImages = []
    elif mode is Mode.replay:
        runId = form.getvalue('replay')
        public = True
        try:
            config = Config(runId)
            bindsPath = config.path.with_suffix('.binds')
            replayPath = config.path.with_suffix('.replay')
            if not (bindsPath.exists() and replayPath.exists):
                raise FileNotFoundError
            with codecs.open(str(bindsPath), 'r', 'utf-8') as fileInput:
                xml = fileInput.read()
            try:
                with replayPath.open("rb") as pickleFile:
                    replayInfo = pickle.load(pickleFile)
                    displayGroups = replayInfo.get('displayGroups',
                                                   ['Galaxy map', 'General', 'Head look', 'SRV', 'Ship', 'UI'])
                    errors.misconfigurationWarnings = replayInfo.get('misconfigurationWarnings',
                                                                     replayInfo.get('warnings', ''))
                    errors.deviceWarnings = replayInfo.get('deviceWarnings', '')
                    errors.unhandledDevicesWarnings = ''
                    styling = replayInfo.get('styling', 'None')
                    description = replayInfo.get('description', '')
                    # devices = replayInfo['devices']
            except FileNotFoundError:
                displayGroups = ['Galaxy map', 'General', 'Head look', 'SRV', 'Ship', 'UI']
        except (ValueError, FileNotFoundError):
            errors.errors = f'<h1>Configuration "{runId}" not found</h1>'
            displayGroups = ['Galaxy map', 'General', 'Head look', 'SRV', 'Ship', 'UI']
            xml = '<root></root>'
    elif mode is Mode.generate:
        config = Config.new_random()
        config.mkdir()
        runId = config.name
        (displayGroups, styling, description) = parseForm(form)
        xml = form.getvalue('bindings')
        if xml is None or xml == b'':
            errors.errors = '<h1>No bindings file supplied; please go back and select your binds file as per the instructions.</h1>'
            xml = '<root></root>'
        else:
            xml = xml.decode(encoding='utf-8')
            bindsPath = config.path.with_suffix('.binds')
            with codecs.open(str(bindsPath), 'w', 'utf-8') as xmlOutput:
                xmlOutput.write(xml)

        public = len(description) > 0
    elif mode is Mode.list:
        deviceFilters = form.getvalue("deviceFilter", [])
        if deviceFilters:
            if type(deviceFilters) is not type([]):
                deviceFilters = [deviceFilters]
            options['controllers'] = set(deviceFilters)

    if mode is Mode.replay or mode is Mode.generate:
        (physicalKeys, modifiers, devices) = parseBindings(runId, xml, displayGroups, errors)

        alreadyHandledDevices = []
        createdImages = []
        for supportedDeviceKey, supportedDevice in SUPPORTED_DEVICES.items():
            if supportedDeviceKey == 'Keyboard':
                # We handle the keyboard separately below
                continue

            for deviceIndex in [0, 1]:
                # See if we handle this device
                handled = False
                for handledDevice in supportedDevice.get('KeyDevices', supportedDevice.get('HandledDevices')):
                    if devices.get(f'{handledDevice}::{deviceIndex}') is not None:
                        handled = True
                        break

                if handled is True:
                    # See if we have any new bindings for this device
                    hasNewBindings = False
                    for device in supportedDevice.get('KeyDevices', supportedDevice.get('HandledDevices')):
                        deviceKey = f'{device}::{deviceIndex}'
                        if deviceKey not in alreadyHandledDevices:
                            hasNewBindings = True
                            break
                    if hasNewBindings is True:
                        createHOTASImage(physicalKeys, modifiers, supportedDevice['Template'],
                                         supportedDevice['HandledDevices'], 40, config, public, styling, deviceIndex,
                                         errors.misconfigurationWarnings)
                        createdImages.append(f'{supportedDeviceKey}::{deviceIndex}')
                        for handledDevice in supportedDevice['HandledDevices']:
                            alreadyHandledDevices.append(f'{handledDevice}::{deviceIndex}')

        if devices.get('Keyboard::0') is not None:
            appendKeyboardImage(createdImages, physicalKeys, modifiers, displayGroups, runId, public)

        for deviceKey, device in devices.items():
            # Arduino Leonardo is used for head tracking so ignore it, along with vJoy (Tobii Eyex) and 16D00AEA (EDTracker)
            if device is None and deviceKey != 'Mouse::0' and deviceKey != 'ArduinoLeonardo::0' and deviceKey != 'vJoy::0' and deviceKey != 'vJoy::1' and deviceKey != '16D00AEA::0':
                logError(f'{runId}: found unsupported device {deviceKey}\n')
                if errors.unhandledDevicesWarnings == '':
                    errors.unhandledDevicesWarnings = '<h1>Unknown controller detected</h1>You have a device that is not supported at this time. Please report details of your device by following the link at the bottom of this page supplying the reference "%s" and we will attempt to add support for it.' % runId
            if device is not None and 'ThrustMasterWarthogCombined' in device[
                'HandledDevices'] and errors.deviceWarnings == '':
                errors.deviceWarnings = '<h2>Mapping Software Detected</h2>You are using the ThrustMaster TARGET software. As a result it is possible that not all of the controls will show up. If you have missing controls then you should remove the mapping from TARGET and map them using Elite\'s own configuration UI.'

        if len(createdImages) == 0 and errors.misconfigurationWarnings == '' and errors.unhandledDevicesWarnings == '' and errors.errors == '':
            errors.errors = '<h1>The file supplied does not have any bindings for a supported controller or keyboard.</h1>'

    # Save variables for later replays
    if (mode is Mode.generate and public):
        saveReplayInfo(config, description, styling, displayGroups, devices, errors)

    printHTML(mode, options, config, public, createdImages, deviceForBlockImage, errors)
