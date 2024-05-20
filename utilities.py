import fitz
from PIL import Image
from io import BytesIO
import boto3
import locale
from datetime import datetime
from dateutil import parser
import re
from fpdf import FPDF
import csv
import io
from botocore.client import BaseClient
from typing import Union
import logging as log

log.basicConfig(level=log.DEBUG)
logger = log.getLogger('Log')

# Generic Functions

def generate_presigned_url(bucket_name: str, object_key: str, expiration=3600) -> Union[str, None]:
    try:
        s3_client = boto3.client('s3')
        response = s3_client.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': object_key}, ExpiresIn=expiration)
        return response
    except Exception as e:
        logger.info(f"Error generating pre-signed URL: {e}")
        return None

def image_to_text(textract_client: BaseClient, image_content: bytes) -> str:
    try:
        textract_response = textract_client.analyze_document(Document={'Bytes': image_content}, FeatureTypes=['TABLES'])
        text_content = ''
        for item in textract_response.get('Blocks', []):
            if item.get('BlockType') == 'LINE':
                text_content += item.get('Text', '') + '\n'
        return text_content.strip()
    except Exception as e:
        logger.error(f"Error extracting text from image: {str(e)}")
        return ''

def format_currency(amount: Union[float, int]) -> str:
    try:
        locale.setlocale(locale.LC_ALL, '')
        return locale.currency(amount, grouping=True)
    except (ValueError, locale.Error) as e:
        return f"Error formatting currency: {str(e)}"

def convert_date(input_date: str) -> str:
    date_object = datetime.strptime(input_date, "%Y-%m-%d")
    return date_object.strftime("%y%m%d")

def convert_to_float(amount_str: str) -> float:
    try:
        amount_str = amount_str.replace(' ', '').replace(',', '')
        if amount_str.startswith('$'):
            amount_str = amount_str[1:]
        if amount_str.endswith('$'):
            amount_str = amount_str[:-1]
        return float(amount_str)
    except ValueError as e:
        logger.error(f"Error converting '{amount_str}' to float: {e}")
        return None

def parse_date(date_str: str) -> str:
    formats = ["%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y", "%B %d, %Y", "%B %d,%Y"]
    if date_str:
        for date_format in formats:
            try:
                parsed_date = datetime.strptime(date_str, date_format)
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                pass
    logger.warning(f"Unable to parse date string '{date_str}'")
    return None

def images_to_pdf(image_paths: list, output_pdf_path: str):
    try:
        pdf = FPDF()
        for image_path in image_paths:
            pdf.add_page()
            pdf.image(image_path, 0, 0, 210, 297)
        pdf.output(output_pdf_path)
        logger.info(f"PDF successfully generated and saved to '{output_pdf_path}'")
    except Exception as e:
        logger.error(f"Error saving images to PDF: {str(e)}")

def correct_customer_name(sentence: str) -> str:
    word = sentence.split('\n')
    if len(word) > 1:
        w = word[0].replace(' ', '')
        if len(w) <= 5 and len(word[1]) > 5:
            return word[1]
        else:
            return word[0]
    else:
        return word[0]

# Feature Extraction Functions

def detect_due_date(text: str) -> tuple:
    try:
        formatted_date = None
        all_date_pattern = re.compile(r'\b(?:\d{1,2}[/]\d{1,2}[/]\d{2,4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)\s\d{1,2},?\s?\d{2,4})\b', flags=re.IGNORECASE)
        due_date_match = re.search(r'\b(?:bill date|payment due date|total amount due|due date):?\s*(\d{1,2}[/]\d{1,2}[/]\d{2,4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)\s\d{1,2},?\s?\d{2,4})\b', text.lower(), flags=re.IGNORECASE)

        if due_date_match:
            extracted_date = due_date_match.group(1)
            formatted_date = datetime.strptime(extracted_date, "%m/%d/%Y").strftime("%Y-%m-%d")
            formatted_date_convert = convert_date(formatted_date) if formatted_date else None
            return formatted_date, formatted_date_convert
        
        elif all_date_pattern:
            date_match = all_date_pattern.findall(text.lower())
            parsed_dates = [parser.parse(match) for match in date_match]
            if parsed_dates:
                date = parsed_dates[0].strftime("%Y-%m-%d")
                formatted_date = date
                formatted_date_convert = convert_date(date) if date else None
                return formatted_date, formatted_date_convert
        else:
            return None, None
    except Exception as e:
        logger.error(f"Error detecting due date: {str(e)}")
        return None, None

def detect_total_amount(text: str) -> Union[float, None]:
    singaltotal_amount_pattern = r"balance due\s*?\$([\d,]+.\d{2})|total amount due\s+\d{2}/\d{2}/\d{4}\s+\$([\d.]+)|total payment due\n?.*?\n?([\d,]+\.\d+)|total due\s*\$([\d.]+)|amount due\s*([\d,.]+)|auto pay:?\s*\$([\d,.]+)|total amount due\s*.*?\n.*?\n\s*\$([\d.]+)|invoice amount\s*?\$([\d,]+.\d{2})"
    all_amount_pattern = re.compile(r'\$(\s*[0-9,]+(?:\.[0-9]{2})?)')
    all_amount_match = all_amount_pattern.search(text.lower())
    match = re.search(singaltotal_amount_pattern, text.lower(), re.DOTALL)

    if match:
        balance_due = next((x for x in match.groups() if x is not None), None) if match else None
        logger.info(f'The balance due exists and it is : {balance_due}')
        return convert_to_float(balance_due)
    elif all_amount_match:
        extracted_amount = all_amount_match.group(1)
        return convert_to_float(extracted_amount)
    else:
        return None

def detect_payable_to(text: str) -> Union[str, None]:
    return None

def detect_payable_from(text: str) -> Union[str, None]:
    customer_name_match1 = re.search(r'billed to:?\n?(.*)|from:\n?(.*)|bill to:?\n?(.*)|site name:?\n?(.*)|(.*)\npo box 853|(.+?)\n(.+?)\n(.+?)p\.o\. box 853|((?:.*\n){3})(po|p.o|p.o.)\s*(box|box) 853|client name:?\s*(.*)',text.lower())
    if customer_name_match1 is not None:
        x = next((x for x in customer_name_match1.groups() if x is not None), "default")
        customer_name = ' '.join(re.findall(r'\b[A-Z][A-Z\s]+\b', x))
        if len(customer_name) > 3:
            return correct_customer_name(customer_name)
        else:
            return correct_customer_name(x)
    else:
        return None

def name_document_with_convention_naming(due_date: str, total_amount: float) -> Union[str, None]:
    try:
        invoice_name = None
        if due_date is not None and total_amount is not None:
            invoice_name = f"{due_date} {format_currency(total_amount)}.pdf"
        elif due_date is None and total_amount is not None:
            invoice_name = f"{format_currency(total_amount)} .pdf"
        else:
            invoice_name = f"{due_date} .pdf"
        return invoice_name
    except Exception as e:
        logger.error(f"Error creating document name: {str(e)}")
        return None

# Document Splitting Functions

def append_due_date_and_amount(dic, current_due_date_converted, current_total_amount):
    if current_due_date_converted is None and current_total_amount is None:
        dic['due date'].append('None')
        dic['total amount'].append('None')
    elif current_due_date_converted is None:
        dic['due date'].append('None')
        dic['total amount'].append(current_total_amount)
    else:
        dic['due date'].append(current_due_date_converted)
        dic['total amount'].append("None")
            
    dic['due date'].append(current_due_date_converted)
    dic['total amount'].append(current_total_amount)

    return dic

def find_first_non_none(dic):
    selected_due_date = None
    selected_total_amount = None
    
    for due_date, total_amount in zip(dic['due date'], dic['total amount']):
        if due_date != 'None':
            selected_due_date = due_date
        if total_amount != 'None':
            selected_total_amount = total_amount
        if selected_due_date is not None and selected_total_amount is not None:
            break
    return selected_due_date, selected_total_amount




def sheet_creator(s3_client: BaseClient, bucket_name: str, prefix_splited_doc: str, splited_doc_name: str, all_csv_data: list, header_written: bool, prefix_sheet_creator: str, due_date: str, total_amount: float, payable_from: str, payable_to: str) -> None:
    try:
        extracted_info = {
            "Payable From": payable_from,
            "Due Date": due_date,
            "Total Amount": total_amount,
            "Payable To": payable_to,
            "Link to PDF": generate_presigned_url(s3_client, bucket_name, f"{prefix_splited_doc}/{splited_doc_name}")
        }

        csv_data = list(extracted_info.values())
        if not header_written:
            header = list(extracted_info.keys())
            all_csv_data.append(header)
            header_written = True

        all_csv_data.append(csv_data)
        
        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerows(all_csv_data)

        s3_client.put_object(Bucket=bucket_name, Key=prefix_sheet_creator, Body=csv_buffer.getvalue())
    except Exception as e:
        logger.error(f"Error creating CSV file and uploading to S3: {str(e)}")

def convert_page_to_image_content(doc_content: bytes, page_number: int) -> bytes:
    try:
        with fitz.open(stream=doc_content, filetype="pdf") as pdf_document:
            pdf_page = pdf_document[page_number - 1]
            zoom_factor = 2.0
            pix = pdf_page.get_pixmap(matrix=fitz.Matrix(zoom_factor, zoom_factor))
            pil_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            jpeg_buffer = BytesIO()
            pil_image.save(jpeg_buffer, format='JPEG', quality=95)
            return jpeg_buffer.getvalue()
    except Exception as e:
        print(f"Error converting page {page_number}: {str(e)}")
        return b''

