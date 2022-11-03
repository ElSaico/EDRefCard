from wand.drawing import Drawing
from wand.image import Image

from data import KEYMAP


def trans_key(key):
    if key is None:
        return None
    trans = KEYMAP.get(key)
    if trans is None:
        trans = key.replace('Key_', '')
    return trans


def layout_text(img: Image, context: Drawing, texts, hotas_detail, biggest_font_size: int):
    width = hotas_detail.get('width')
    height = hotas_detail.get('height', 54)

    # Work out the best font size
    font_size = best_fit_font_size(context, width, height, texts, biggest_font_size)

    # Work out location of individual texts
    current_x = hotas_detail.get('x')
    current_y = hotas_detail.get('y')
    max_x = hotas_detail.get('x') + hotas_detail.get('width')

    for text in texts:
        text['Size'] = font_size
        context.font = text['Style']['Font']
        context.font_size = font_size
        metrics = context.get_font_metrics(img, text['Text'], multiline=False)
        if current_x + int(metrics.text_width) > max_x:
            # Newline
            current_x = hotas_detail.get('x')
            current_y += font_size
        text['X'] = current_x
        text['Y'] = current_y + int(metrics.ascender)
        current_x += int(metrics.text_width + metrics.character_width)

    # We want to centre the texts vertically, which we can now do as we know how much space the texts take up
    text_height = current_y + font_size - hotas_detail.get('y')
    y_offset = int((height - text_height) / 2) - int(font_size / 6)
    for text in texts:
        text['Y'] += y_offset

    return texts


# Calculate the best fit font size for our text given the dimensions of the box
def best_fit_font_size(context: Drawing, width: int, height: int, texts, biggest_font_size: int):
    font_size = biggest_font_size
    context.push()
    with Image(width=width, height=height) as img:
        # Step through the font size until we find one that fits
        fits = False
        while not fits:
            current_x = 0
            current_y = 0
            too_long = False
            for text in texts:
                context.font = text['Style']['Font']
                context.font_size = font_size
                metrics = context.get_font_metrics(img, text['Text'], multiline=False)
                if current_x + int(metrics.text_width) > width:
                    if current_x == 0:
                        # This single entry is too long for the box; shrink it
                        too_long = True
                        break
                    else:
                        # Newline
                        current_x = 0
                        current_y += font_size
                text['X'] = current_x
                text['Y'] = current_y + int(metrics.ascender)
                current_x += int(metrics.text_width + metrics.character_width)
            if not too_long and current_y + metrics.text_height < height:
                fits = True
            else:
                font_size -= 1
    context.pop()
    return font_size
