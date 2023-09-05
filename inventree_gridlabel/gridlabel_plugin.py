"""
Label printing plugin for InvenTree.
Supports direct printing of labels on label printers
"""
# translation
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MinValueValidator
from django.core.validators import MaxValueValidator

# InvenTree plugin libs
from label.models import LabelOutput, LabelTemplate
from plugin import InvenTreePlugin
from plugin.mixins import LabelPrintingMixin, SettingsMixin

# Plugin libs
from PIL import Image

from inventree_gridlabel.version import GRIDLABEL_PLUGIN_VERSION

# Constants
FORMATS_MM = {
    "DIN A0": (841, 1189),
    "DIN A1": (594, 841),
    "DIN A2": (420, 594),
    "DIN A3": (297, 420),
    "DIN A4": (210, 297),
    "DIN A5": (148, 210),
    "DIN A6": (105, 148),
    "DIN A7": (74, 105),
    "DIN A8": (52, 74),
}

CONVERSION_RATE_MM_TO_PX = 25.4


class GridLabelPlugin(LabelPrintingMixin, SettingsMixin, InvenTreePlugin):

    AUTHOR = "Niklas Diehm"
    DESCRIPTION = "Inventree plugin for printing labels on a grid"
    VERSION = GRIDLABEL_PLUGIN_VERSION
    NAME = "GridLabel"
    SLUG = "gridlabel"
    TITLE = "Grid Label Printer"

    SETTINGS = {
        'PAPER_FORMAT': {
            'name': _('Paper format'),
            'description': _('Select paper format'),
            'choices': [
                ('DIN A0', 'DIN A0'),
                ('DIN A1', 'DIN A1'),
                ('DIN A2', 'DIN A2'),
                ('DIN A3', 'DIN A3'),
                ('DIN A4', 'DIN A4'),
                ('DIN A5', 'DIN A5'),
                ('DIN A6', 'DIN A6'),
                ('DIN A7', 'DIN A7'),
                ('DIN A8', 'DIN A8'),
                ],
            'default': 'DIN A4',
        },
        'LANDSCAPE': {
            'name': _('Landscape mode'),
            'description': _('Use landscape mode for creating labels'),
            'validator': bool,
            'default': False,
        },
        'VERTICAL': {
            'name': _('Vertical'),
            'description': _('Place next label below the previous one instead of next to it'),
            'validator': bool,
            'default': False,
        },
        'DPI': {
            'name': _('DPI'),
            'description': _('DPI of the printer'),
            'validator': [int, MinValueValidator(0), MaxValueValidator(1200)],
            'default': 300,
        },
        'HORIZONTAL_PADDING': {
            'name': _('Horizontal padding'),
            'description': _('Horizontal padding between labels in mm'),
            'validator': [int, MinValueValidator(0), MaxValueValidator(1200)],
            'default': 5,
        },
        'VERTICAL_PADDING': {
            'name': _('Vertical padding'),
            'description': _('Vertical padding between labels in mm'),
            'validator': [int, MinValueValidator(0), MaxValueValidator(1200)],
            'default': 5,
        },
    }

    def print_label(self, label: LabelTemplate, request, **kwargs):
        """Handle printing of a single label.

        Returns either a PDF or HTML output, depending on the DEBUG setting.
        """

        dpi = self.get_setting('DPI')
        return_picture = kwargs.get('picture', False)

        if return_picture:
            return self.render_to_png(label, request, dpi=dpi, **kwargs)
        else:
            return self.render_to_pdf(label, request, **kwargs)

    def print_labels(self, label: LabelTemplate, items: list, request, **kwargs):
        """Handle printing of multiple labels

        - Label outputs are concatenated together, and we return a single PDF file.
        - If DEBUG mode is enabled, we return a single HTML file.
        """

        landscape = self.get_setting('LANDSCAPE')
        horizontal_padding = self.get_setting('HORIZONTAL_PADDING')
        vertical_padding = self.get_setting('VERTICAL_PADDING')
        vertical = self.get_setting('VERTICAL')
        dpi = int(self.get_setting('DPI'))
        format_printing = self.get_setting('PAPER_FORMAT')

        horizontal_padding = int((horizontal_padding * dpi) / CONVERSION_RATE_MM_TO_PX)
        vertical_padding = int((vertical_padding * dpi) / CONVERSION_RATE_MM_TO_PX)

        mm = FORMATS_MM[format_printing]

        site_0 = int((mm[0] * dpi) / CONVERSION_RATE_MM_TO_PX)
        site_1 = int((mm[1] * dpi) / CONVERSION_RATE_MM_TO_PX)

        if landscape:
            base_page = Image.new(
                'L',
                (site_1, site_0),
                color='white')
        else:
            base_page = Image.new(
                'L',
                (site_0, site_1),
                color='white')

        outputs = []
        output_file = None

        for item in items:
            label.object_to_print = item
            outputs.append(self.print_label(label, request, picture=True, **kwargs))

        pages = []
        pages.append(base_page.copy())
        current_page = 0
        current_max_x = 0
        current_max_y = 0

        for output in outputs:
            # Check if there is enough space on the page
            if vertical:
                # Check if there is enough space below
                if current_max_y + output.height + vertical_padding > base_page.height:
                    # Not enough space, check if there is enough space on the right
                    if current_max_x + 2*(output.width + horizontal_padding) > base_page.width:
                        # Not enough space on the right, create a new page
                        pages.append(base_page.copy())
                        current_page += 1
                        current_max_x = 0
                        current_max_y = 0
                    else:
                        # Enough space on the right, so move the cursor there
                        current_max_x += output.width + horizontal_padding
                        current_max_y = 0
                # Now we have enough space, so paste in the label
                pages[current_page].paste(output, (current_max_x, current_max_y))
                current_max_y += output.height + vertical_padding
            else:
                # Check if there is enough space on the right
                if current_max_x + output.width + horizontal_padding > base_page.width:
                    # Not enough space, check if there is enough space below
                    if current_max_y + 2*(output.height + vertical_padding) > base_page.height:
                        # Not enough space below, create a new page
                        pages.append(base_page.copy())
                        current_page += 1
                        current_max_x = 0
                        current_max_y = 0
                    else:
                        # Enough space below, so move the cursor there
                        current_max_y += output.height + vertical_padding
                        current_max_x = 0
                # Now we have enough space, so paste in the label
                pages[current_page].paste(output, (current_max_x, current_max_y))
                current_max_x += output.width + horizontal_padding

        # Put the pages together into a single PDF
        pages[0].save('labels.pdf', save_all=True, append_images=pages[1:], title="Labels")

        # Load created file into memory
        with open('labels.pdf', 'rb') as pdf_file:
            pdf = pdf_file.read()

        # Create label output file
        output_file = ContentFile(pdf, 'labels.pdf')

        # Save the generated file to the database
        output = LabelOutput.objects.create(
            label=output_file,
            user=request.user
        )

        return JsonResponse({
            'file': output.label.url,
            'success': True,
            'message': f'{len(items)} labels generated'
        })
