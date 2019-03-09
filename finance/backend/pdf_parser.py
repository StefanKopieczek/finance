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


def get_pdf_transactions(path):
    raw_row_data = get_text_rows(path)
    pages = paginate_rows(raw_row_data)
    for page in pages:
        extract_transactions_from_page(page)


def extract_transactions_from_page(page):
    rows_iter = iter(page)
    try:
        header_columns = extract_header_columns(rows_iter)
    except KeyError:
        # No headers, so this page doesn't have any transactions
        return

    for row in rows_iter:
        date, payment_type, details, paid_out, paid_in = parse_transaction_row(row, header_columns)
        if row_is_valid(date, payment_type, details, paid_out, paid_in):
            print(date, payment_type, details, paid_out, paid_in)


def parse_transaction_row(row, header_columns):
    parsed_columns = [None, None, None, None]
    payment_details = None
    unparsed_columns = []
    for column, value in row:
        for col_type, col_type_x in enumerate(header_columns):
            if abs(column - col_type_x) < 20:
                parsed_columns[col_type] = value
                break
        else:
            unparsed_columns.append((column, value))
    if len(unparsed_columns) > 1:
        return None, None, None, None, None
    elif len(unparsed_columns) == 1:
        column, value = unparsed_columns[0]
        if column > header_columns[1] and column < header_columns[2]:
            payment_details = value
        else:
            return None, None, None, None, None
    date, payment_type, paid_out, paid_in = parsed_columns
    return date, payment_type, payment_details, paid_out, paid_in


def row_is_valid(*args):
    if args[2] is None:
        return False
    if 'BALANCE BROUGHT FORWARD' in args[2]:
        return False
    if 'BALANCE CARRIED FORWARD' in args[2]:
        return False
    return True


def extract_header_columns(page):
    for columns in page:
        if 'Date' in columns[0][1]:
            break
    else:
        raise KeyError("No headers on this page")

    return [columns[col][0] for col in range(4)]


def paginate_rows(raw_rows):
    page = []
    page_id = -1
    for row in raw_rows:
        if page_id == -1:
            page_id = row[0]
        elif page_id != row[0]:
            yield page
            page = [row[2]]
            page_id = row[0]
        page.append(row[2])


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
    laparams.line_overlap = 0.01
    laparams.line_margin = 0.01
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
        rows[key] = sorted(rows[key])
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
