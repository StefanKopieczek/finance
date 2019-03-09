import datetime
import re
from .api import Transaction
from collections import defaultdict
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator
import pdfminer
from more_itertools import peekable


def get_pdf_transactions(path):
    raw_row_data = get_text_rows(path)
    pages = paginate_rows(raw_row_data)
    for page in pages:
        for row in page:
            print(row)


def paginate_rows(raw_rows):
    def build_one_page(raw_rows):
        raw_rows = peekable(raw_rows)
        try:
            raw_row = next(raw_rows)
            page, _, _ = raw_row
            yield raw_row
            while raw_rows.peek()[0] == page:
                yield next(raw_rows)
        except StopIteration:
            pass
        return

    while True:
        yield build_one_page(raw_rows)


def get_text_rows(path):
    rows = defaultdict(list)
    # Open a PDF file.
    fp = open(path, 'rb')

    # Create a PDF parser object associated with the file object.
    # parser = PDFParser(fp)

    # Create a PDF document object that stores the document structure.
    # Password for initialization as 2nd parameter
    # document = PDFDocument(parser)

    # Check if the document allows text extraction. If not, abort.
    # if not document.is_extractable:
    #     raise PDFTextExtractionNotAllowed

    # Create a PDF resource manager object that stores shared resources.
    rsrcmgr = PDFResourceManager()

    # Create a PDF device object.
    device = PDFDevice(rsrcmgr)

    # BEGIN LAYOUT ANALYSIS
    # Set parameters for analysis.
    laparams = LAParams()
    laparams.line_overlap = 0.1
    laparams.line_margin = 0.1
    laparams.word_margin = 0.15

    # Create a PDF page aggregator object.
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)

    # Create a PDF interpreter object.
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    def parse_obj(lt_objs, page):
        # loop over the object list
        for obj in lt_objs:
            # if it's a textbox, print text and location
            if isinstance(obj, pdfminer.layout.LTTextBoxHorizontal):
                rows[(page, -int(obj.bbox[1]))].append((int(obj.bbox[0]), repr(obj.get_text().replace('\n', '_'))))
            # if it's a container, recurse
            elif isinstance(obj, pdfminer.layout.LTFigure):
                parse_obj(obj._objs, page)

    # loop over all pages in the document
    for page_num, page in enumerate(PDFPage.get_pages(fp)):
        # read the page into a layout object
        interpreter.process_page(page)
        layout = device.get_result()

        # extract text from this object
        parse_obj(layout._objs, page_num)

    for key in sorted(rows):
        page, y = key
        y = -y
        yield (page, y, rows[key])


def parse_row(row):
    date, description, quantity = row
    date = datetime.datetime.strptime(date, '%d/%m/%Y')
    description = re.sub(' {2,}', ' - ', description)
    quantity = -int(re.sub('[.,]', '', quantity))
    return Transaction(
        None,
        date,
        description,
        quantity,
    )
