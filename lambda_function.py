                            #########################################################
                            #                                                       #
                            #          Section A: Import Libraries                  #
                            #                                                       #
                            #########################################################
import re
import os
import cv2 as cv
import numpy as np
from fpdf import FPDF
import csv
import io
import concurrent.futures
from  botocore.client import BaseClient
from typing import Union
import logging
import fitz
from io import BytesIO
from PIL import Image
import boto3
import locale   
from datetime import datetime
from dateutil import parser

#Additionnaly lib for sheet_creator function
import openpyxl
from openpyxl import Workbook
from io import BytesIO


                            #########################################################
                            #                                                       #
                            #          Section B: Define Variables                  #
                            #                                                       #
                            #########################################################

#----------- Logging is used for traking events that occur while the program is running -------
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('Log')
# Initialize AWS clients
s3_client = boto3.client('s3')  # S3 client
textract_client = boto3.client('textract')  # Textract client
splited_doc_folder = os.environ.get('FOLDER_SPLITED_DOC')
output_folder = os.environ.get('FOLDER_Sheet_OUTPUT')


                            #########################################################
                            #                                                       #
                            #         Section C:    Relative Functions funtion      #
                            #                                                       #
                            #########################################################


# Function: Image to text is used to consume amazon textract in order to extract informations from Image Done!
def Scannedimage_content_to_text(image_content: bytes) -> str:
    
    try:
        # Start a Textract job to detect text in the specified image
        textract_response = textract_client.analyze_document(Document={'Bytes': image_content}, FeatureTypes=['TABLES'])

        text_content = ''
        # Extract text content from Textract response blocks
        for item in textract_response.get('Blocks', []):
            if item.get('BlockType') == 'LINE':
                text_content += item.get('Text', '') + '\n'

        return text_content.strip()  # Return the extracted text content from the image

    except Exception as e:
        logging.error(f"Error extracting text from image: {str(e)}")
        return ''


# Convert a specific page of a PDF document to image content.   Done!!
def Scannedpage_tobyte(doc_content: bytes, page_number: int) -> bytes:
    
    try:
        # Open the PDF file using PyMuPDF (fitz) library
        with fitz.open(stream=doc_content, filetype="pdf") as pdf_document:
            # Get the specific page from the PDF
            pdf_page = pdf_document[page_number - 1]

            # Set the resolution for better quality
            zoom_factor = 2.0
            pix = pdf_page.get_pixmap(matrix=fitz.Matrix(zoom_factor, zoom_factor))

            # Create a PIL Image from the pixmap
            pil_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Convert the image to JPEG format with better quality settings
            jpeg_buffer = BytesIO() # Initiate an empty image
            pil_image.save(jpeg_buffer, format='JPEG', quality=95) # Save the image buffer in the setting PIL Image 

            # Return the BytesIO buffer containing the converted JPEG image
            return jpeg_buffer.getvalue()

    except Exception as e:
        # Handle any exceptions that may occur during the conversion and print an error message
        error_message = "Error converting page {}: {}".format(page_number, str(e))
        print(error_message)

        return b''  # Return an empty bytes object if an error occurs
#  Convert the extracted date to DD/MM/YYYY format - Done!
def to_YYMMDD(input_date: str)-> str:
    
    # Convert string to datetime object
    date_object = datetime.strptime(input_date, "%d/%m/%Y")
    # Format the datetime object as ymd (year-month-day without separators)
    output_format = date_object.strftime("%y%m%d")

    return output_format

# Function to convert string to float based on condition in review
def to_float(amount_str: str) -> float:
    # Remove dollar sign if present
    amount_str = amount_str.replace('$', '')
    # Remove commas and spaces
    amount_str = amount_str.replace(',', '').replace(' ', '')
    try:
        # Convert the string to a float
        amount_float = float(amount_str)

        # Log successful conversion
        logging.info(f"Successfully converted '{amount_str}' to float: {amount_float}")
        return amount_float
    except ValueError:
        # Log conversion failure
        logging.error(f"Failed to convert '{amount_str}' to float")
        raise

# Transform Loaded PDF file into Image. Done!!
def Convert_doc_to_images(pdf_content: bytes) -> list:
    try:
        list_images = []    # List of converted pdf pages to images

        # Loop through all pages of the pdf and convert them into images
        for i in range(1, len(fitz.open(stream=pdf_content, filetype="pdf")) + 1):
            image_content = Scannedpage_tobyte(pdf_content, i)
            list_images.append(image_content)

        return list_images

    except Exception as e:
        return { 
            "Title": "Error converting PDF to images" ,
            "error": "{}".format(str(e))
        }


#   Restruct the function based on  return filter in review
def filter_payblefrom(sentence: str)-> str:
    word=sentence.split('\n')
    if len(word)>1:
        w=word[0].replace(' ','')
        
        if len(w)<=5 and len(word[1])>5:
            result  = word[1]
                   
        else:
            result  = word[0]
    else:
         result  = word[0]
    return result



                            #########################################################
                            #                                                       #
                            #     Section D:  extraction Features Funtions R.F      #
                            #                                                       #
                            #########################################################

def extract_due_date(text: str) -> tuple:
    try:
        # Regular expression pattern to match dates
        all_date_pattern = re.compile(r'\b(?:\d{1,2}[/]\d{1,2}[/]\d{2,4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)\s\d{1,2},?\s?\d{2,4})\b', flags=re.IGNORECASE)
        # Search for due date pattern in the text
        due_date_match = re.search(r'\b(?:bill date|payment due date|total amount due|due date):?\s*(\d{1,2}[/]\d{1,2}[/]\d{2,4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)\s\d{1,2},?\s?\d{2,4})\b', text.lower(), flags=re.IGNORECASE)
        

        if due_date_match:
            # Extract the due date from the match
            extracted_date = due_date_match.group(1)
            logging.debug(f'This is the extracted Date: {extracted_date}')
            
            # Convert the extracted date to DD/MM/YYYY format
            formatted_date = datetime.strptime(extracted_date, "%m/%d/%Y").strftime("%d/%m/%Y")
            
            # Convert the formatted date to YYMMDD format
            formatted_date_convert = to_YYMMDD(formatted_date) if formatted_date else None
            
            return formatted_date, formatted_date_convert
        
        elif all_date_pattern:
            # Find all matches in the text
            date_match = all_date_pattern.findall(text.lower())

            # Parse the found dates using dateutil.parser
            parsed_dates = [parser.parse(match) for match in date_match]

            # If a date is found, format it
            if parsed_dates:
                date = parsed_dates[0].strftime("%d/%m/%Y")
                formatted_date = date
                formatted_date_convert = to_YYMMDD(date) if date else None
                return formatted_date, formatted_date_convert
        else:
            return None, None

    except Exception as e:
        logging.error(f"Error extracting  due date: {str(e)}")
        return None, None

def extract_total_amount(text: str) -> Union[float, None]:
    try:
        # Regular expression patterns
        single_total_amount_pattern = r"balance due\s*?\$([\d,]+.\d{2})|total amount due\s+\d{2}/\d{2}/\d{4}\s+\$([\d.]+)|total payment due\n?.*?\n?([\d,]+\.\d+)|total due\s*\$([\d.]+)|amount due\s*([\d,.]+)|auto pay:?\s*\$([\d,.]+)|total amount due\s*.*?\n.*?\n\s*\$([\d.]+)|invoice amount\s*?\$([\d,]+.\d{2})"
        all_amount_pattern = re.compile(r'\$(\s*[0-9,]+(?:\.[0-9]{2})?)')

        # Search for all amounts in the text
        all_amount_match = all_amount_pattern.search(text.lower())
        
        # Search for only the total amount in the text
        match = re.search(single_total_amount_pattern, text.lower(), re.DOTALL)

        # Check if a match is found
        if match:
            balance_due = next((x for x in match.groups() if x is not None), None)
            logging.info(f'The balance due exists and it is: {balance_due}')
            return to_float(balance_due)

        elif all_amount_match:
            
            return to_float(all_amount_match.group(1))

        else:
            return None

    except Exception as e:
        logging.error(f"Error detecting total amount: {str(e)}")
        return None

def extract_payable_from(text: str)-> Union[str,None]:
    
    customer_name_match1 = re.search(r'billed to:?\n?(.*)|from:\n?(.*)|bill to:?\n?(.*)|site name:?\n?(.*)|(.*)\npo box 853|(.+?)\n(.+?)\n(.+?)p\.o\. box 853|((?:.*\n){3})(po|p.o|p.o.)\s*(box|box) 853|client name:?\s*(.*)',text.lower())

    if customer_name_match1 is not None :
        x=next((x for x in customer_name_match1.groups() if x is not None), "default") 
    
        payablefrom = ' '.join(re.findall(r'\b[A-Z][A-Z\s]+\b', x))
        if len(payablefrom)>3:
            c=  payablefrom
        else:
            c=  x
        return  filter_payblefrom(c)
                            
    else:
        return None

# we haven't implemented yet -------- need deep learning and O
def extract_payable_to(text: str)-> str:
   
   
    pass
    return 

# extraction features information
def extraction_totalamount_duedate_payableto_payablefrom(
    content_image: bytes
    ) -> tuple:
    
    try:
        # Convert Image to text
        text = Scannedimage_content_to_text(content_image)
        
        # Define functions to be executed concurrently
        functions = [extract_payable_from, extract_due_date, extract_total_amount, extract_payable_to]
        
        # Create a ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Submit the tasks for parallel execution and get results
            results = list(executor.map(lambda f: f(text), functions))
        
        # Unpack the results
        payable_from, (due_date, due_date_converted), total_amount, payable_to = results
        
        # Return a tuple containing the due date and total payment
        return due_date, due_date_converted, total_amount, payable_from, payable_to
    
    except Exception as e:
        # Handle exceptions
        print(f"An error occurred during features extraction: {e}")
        return (None, None, None, None, None)




                            #########################################################
                            #                                                       #
                            #       Section E: Main Feature Extraction functions    #
                            #                                                       #
                            #########################################################

# Load document file from s3 bucket in review:
def Download_doc(s3_client,Bucket_name,s3_key) -> bytes:

    try:

        response=   s3_client.get_object(Bucket=Bucket_name, Key=s3_key)
        doc=    response['Body'].read()
        return doc

    except Exception as e:
        logger.error(f'Error Downloding Document from S3 Bucket: {str(e)}')

    return 0



# Process document
def Process_doc(bucket_name,prefix_splited_doc: str,doc,all_csv_data: list,prefix_sheet_creator: str,header_written:bool)-> None:


    try:

        pass
    except Exception as e:

        logger.error(f"Error process Document : {str(e)}")



def Upload_doc(np_array: list, bucket_name: str, prefix_splited_doc: str, doc_name: str, temp_pdf_name: str)-> None:

    try:
        # put Process logic here
        pass

    except Exception as e:
        logger.error(f"Error Upload Document to S3 Bucket: {str(e)}")

#############################################NEW CODE##################################
# Refactored function
def upload_doc(
    s3_client: BaseClient,
    np_array: list,
    bucket_name: str,
    prefix_splited_doc: str,
    doc_name: str,
    temp_pdf_name: str
) -> None:

    try:
        # Create temporary image paths and save images
        temp_image_paths = [
            f"/tmp/image_{i}.jpg"
            for i, np_img in enumerate(np_array)
        ]

        for path, np_img in zip(temp_image_paths, np_array):
            # Convert NumPy array to BGR format
            cv_img = cv.cvtColor(np_img, cv.COLOR_RGB2BGR)

            # Encode image as JPEG
            _, img_bytes = cv.imencode('.jpg', cv_img)

            # Save JPEG to temporary path
            with open(path, 'wb') as img_file:
                img_file.write(img_bytes)

        # Generate PDF from images
        save_images_to_pdf(temp_image_paths, temp_pdf_name)

        # Define S3 key for the PDF
        s3_key = f"{prefix_splited_doc}/{doc_name}"

        # Upload PDF to S3
        with open(temp_pdf_name, 'rb') as pdf_file:
            s3_client.upload_fileobj(pdf_file, bucket_name, s3_key)

        logging.info(f"Successfully uploaded PDF to S3: s3://{bucket_name}/{s3_key}")

    except Exception as e:
        logging.error(f"Failed to save images to PDF and upload to S3: {str(e)}")


#############################################NEW CODE excel_creator ##################################

def excel_creator(
    s3_client: BaseClient,
    bucket_name: str,
    prefix_splited_doc: str,
    splited_doc_name: str,
    all_data: list,
    header_written: bool,
    prefix_sheet_creator: str,
    due_date: str,
    total_amount: float,
    payable_from: str,
    payable_to: str
) -> None:
    try:
        # Initialize a dictionary to store extracted features information
        extracted_info = {
            "Payable From": payable_from,
            "Due Date": due_date,
            "Total Amount": total_amount,
            "Payable To": payable_to,
            "Link to PDF": generate_presigned_url(s3_client, bucket_name, f"{prefix_splited_doc}/{splited_doc_name}") # generate_presigned_url function not generate yet
        }

        # Convert extracted information to a list for the Excel
        excel_data = list(extracted_info.values())
        
        if not header_written:
            # Write header only if it hasn't been written before
            header = list(extracted_info.keys())
            all_data.append(header)
            header_written = True

        # Append the current row of data to the overall Excel data
        all_data.append(excel_data)

        # Create a workbook and add the data to the sheet
        wb = Workbook()
        ws = wb.active

        for row in all_data:
            ws.append(row)

        # Save data to a BytesIO buffer
        excel_buffer = BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)

        # Upload the Excel file to the specified S3 bucket
        s3_client.put_object(
            Bucket=bucket_name,
            Key=prefix_sheet_creator,
            Body=excel_buffer.getvalue(),
            ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        # Handle any exceptions that may occur during the process and print an error message
        logging.error(f"Error creating Excel file and uploading to S3: {str(e)}")
        return None


                            #########################################################
                            #                                                       #
                            #         Section F: main handler funtion               #
                            #                                                       #
                            #########################################################


def lambda_handler(event,context):

    try: 
        for record in event['Records']:
            # Retrieve bucket name and object key
            bucket_name = record['s3']['bucket']['name']
            doc_key = record['s3']['object']['key']
        
            # Called function 'Load_document' to load document from s3.
            doc_content = Download_doc(bucket_name,s3_client, doc_key)
                
            # Check if the object is a PDF file
            if doc_key.lower().endswith('.pdf'):
                
                pass
             
    except Exception as e:
        
        logging.error(f"Error handling event: {str(e)}")
    
    return {
        'statusCode':200,
        'body':'everthing was going successfully'
    }
