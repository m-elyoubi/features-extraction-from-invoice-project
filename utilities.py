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
import pandas as pd

log.basicConfig(level=log.DEBUG)
logger = log.getLogger('Log')

# Generic Functions

# The pre-signed URL grants temporary access to download the specified splited document from the S3 bucket. in review
def create_preauthenticated_url(bucket_name: str, object_key: str, expiration=3600)-> Union[str,None]:
    
    try:
        # Initialize an S3 client
        s3_client = boto3.client('s3')

        # Generate the pre-signed URL for the 'get_object' operation on the specified object
        response = s3_client.generate_presigned_url(
            'get_object',     # The operation to perform on the object (e.g., 'get_object' for downloading)
            Params={'Bucket': bucket_name, 'Key': object_key},  # Parameters specifying the bucket and object key
            ExpiresIn=expiration  # Duration in seconds for which the URL will be valid
        )

        return response
    
    except Exception as e:
        # Handle any exceptions that may occur during the generation of the pre-signed URL
        log.info(f"Error generating pre-signed URL: {e}")
        return None

# Function: Image to text is used to consume amazon textract in order to extract informations from Image Done!
def image_to_text(textract_client: BaseClient, image_content: bytes) -> str:
    
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
        log.error(f"Error extracting text from image: {str(e)}")
        return ''

#   This Function has an objective to manage the currency symbole $ - Done! 
def format_currency(amount: Union[float, int]) -> str:
    
    try:
        # Set the locale to the user's default for currency formatting
        locale.setlocale(locale.LC_ALL, '')

        # Format the amount as a currency string with grouping
        formatted_currency = locale.currency(amount, grouping=True)

        return formatted_currency

    except (ValueError, locale.Error) as e:
        # Handle errors related to invalid input or locale settings
        return f"Error formatting currency: {str(e)}"
# logging.info(f'format_currency:{format_currency(347857.9)}') tested done!

# Converts a date string in the format 'YYYY-MM-DD' to 'YYMMDD' format - Done!
def to_YYMMDD(input_date: str)-> str:
     
    # Convert string to datetime object
    date_object = datetime.strptime(input_date, "%Y-%m-%d")

    # Format the datetime object as ymd (year-month-day without separators)
    output_format = date_object.strftime("%y%m%d")
    return output_format
# logging.info(f'to_YYMMDD:{to_YYMMDD("2024-04-30")}') #tested done!

# Function to convert string to float based on condition - 
#   Todo: Manage all position of dollar symbole in the following scenario : ex : $ 6,66 , 56,66.00$  in review!
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
        log.info(f"Successfully converted '{amount_str}' to float: {amount_float}")
        return amount_float
    except ValueError:
        # Log conversion failure
        log.error(f"Failed to convert '{amount_str}' to float")
        raise


# logging.info(f'to_float:{to_float("$ 6,66")}') #tested done!


#Save a list of images into a single PDF file  in review !
def save_images_to_pdf(image_paths :list, output_pdf_path : str):
    
    try:
        # Initialize an instance of the FPDF class
        pdf = FPDF()  # Used FPDF Lib

        # Loop through each image path in the list
        for image_path in image_paths:
            # Add a new page to the PDF for each image
            pdf.add_page()
            
            # Add the image to the current page with specified dimensions (adjust as needed)
            pdf.image(image_path, 0, 0, 210, 297)

        # Output the generated PDF to the specified file path
        pdf.output(output_pdf_path)
        log.info(f"PDF successfully generated and saved to '{output_pdf_path}'")
    except Exception as e:
        # Handle any exceptions that may occur during the process and print an error message
        return (f"Error saving images to PDF: {str(e)}")


# Feature Extraction Functions

#   Fct 1: Sub function to get due_date feature  - Done! 
def extract_due_date(text: str) -> tuple:
    
    try:
        formatted_date = None

        # Regular expression pattern to match dates
        all_date_pattern = re.compile(r'\b(?:\d{1,2}[/]\d{1,2}[/]\d{2,4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)\s\d{1,2},?\s?\d{2,4})\b', flags=re.IGNORECASE)
        
        # Search for due date pattern in the text
        due_date_match = re.search(r'\b(?:bill date|payment due date|total amount due|due date):?\s*(\d{1,2}[/]\d{1,2}[/]\d{2,4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)\s\d{1,2},?\s?\d{2,4})\b', text.lower(), flags=re.IGNORECASE)

        if due_date_match:
            # Extract the due date from the match
            extracted_date = due_date_match.group(1)
            log.debug(f'This is the extracted Date: {extracted_date}')
            
            # Convert the extracted date to YYYY-MM-DD format
            formatted_date = datetime.strptime(extracted_date, "%m/%d/%Y").strftime("%Y-%m-%d")
            
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
                date = parsed_dates[0].strftime("%Y-%m-%d")
                formatted_date = date
                formatted_date_convert = to_YYMMDD(date) if date else None
                return (formatted_date, formatted_date_convert)
        else:
            return (None, None)

    except Exception as e:
        log.error(f"Error detecting due date: {str(e)}")
        return (None, None)

#   Fct 2: Sub function to get totale amount  - Done! 
def extract_total_amount(text: str)-> Union[float,None]:
        
    singaltotal_amount_pattern = r"balance due\s*?\$([\d,]+.\d{2})|total amount due\s+\d{2}/\d{2}/\d{4}\s+\$([\d.]+)|total payment due\n?.*?\n?([\d,]+\.\d+)|total due\s*\$([\d.]+)|amount due\s*([\d,.]+)|auto pay:?\s*\$([\d,.]+)|total amount due\s*.*?\n.*?\n\s*\$([\d.]+)|invoice amount\s*?\$([\d,]+.\d{2})"
    all_amount_pattern = re.compile(r'\$(\s*[0-9,]+(?:\.[0-9]{2})?)')
   
    # Search for all the amount in the text
    all_amount_match = all_amount_pattern.search(text.lower())
    # Search for only the total amount in the text   
    match = re.search(singaltotal_amount_pattern, text.lower(), re.DOTALL)

    # Check if a match is found
    if match:
        balance_due = next((x for x in match.groups() if x is not None), None) if match else None
        log.info(f'The balence due exsit and it is : {balance_due}')
        return to_float(balance_due)

    elif all_amount_match:
       extracted_amount = all_amount_match.group(1)
       return  to_float(extracted_amount)
    
    else:
        return None

def filter_payblefrom(sentence: str) -> str:
    # Split the sentence by whitespace
    words = sentence.split()
    # Initialize an empty list to hold the parts of the name
    name_parts = []
    
    # Loop through the words to find the part that is a number (indicating the start of the address)
    for word in words:
        if word.isdigit() or word.endswith(',') or re.match(r'\d', word):
            break
        name_parts.append(word)
    
    # Join the name parts to form the full name
    full_name = ' '.join(name_parts)
    return full_name

#   Fct 3: Sub function to get paybale from feature  
def extract_payable_from(text: str) -> Union[str, None]:
    # Define a regular expression to find the name and address line
    customer_name_match = re.search(r'billed to:?\n?(.*)|from:\n?(.*)|bill to:?\n?(.*)|site name:?\n?(.*)|(.*)\npo box 853|(.+?)\n(.+?)\n(.+?)p\.o\. box 853|((?:.*\n){3})(po|p.o|p.o.)\s*(box|box) 853|client name:?\s*(.*)|receiver:\s*([^@]+)@|bill to:?\s*(.*)', text.lower(), re.IGNORECASE)
    
    if customer_name_match is not None:
        # Get the matched group
        x =next((x for x in customer_name_match.groups() if x is not None),None) if customer_name_match else None
        return filter_payblefrom(x)
    else:
        log.info("Company name not found.")
        return None
#   Fct 4: Sub function to get paybale feature in review! Try to cover all scenarios (\t, \n, ...)
def extract_payable_to(text: str) -> Union[str, None]:
    # Define a regular expression to find the name and address line
    customer_name_match = re.search(r'sender:\s*([^@]+)@|company:\s*(.*)\n', text.lower(), re.IGNORECASE)
    
    if customer_name_match is not None:
        # Get the matched group
        x =next((x for x in customer_name_match.groups() if x is not None),None) if customer_name_match else None
        log.info(f"Company name is {x}")
        return x
    else:
        log.info("Company name not found.")
        return None
    
#   Fct 5: Sub function to get invoice number feature in review! Try to cover all scenarios (\t, \n, ...)
def extract_InvoiceNumber(text:str )->Union[str,None]:   
    # Define a regular expression pattern to match the invoice number
    pattern = r"invoice number:\s*(\w+)"
    # Use re.search to find the pattern in the text
    match = re.search(pattern, text.lower())
    
    # Extract the invoice number if found
    if match:
        invoice_number = match.group(1)
        log.info(f"Invoice Number: {invoice_number}")
    else:
        log.info("Invoice Number not found")

#   Fct 6: name file based on whatever detected features in {Feat.2} {$Feat.1} {Feat.3} {Feat.4 }.pdf format in review
def name_document_with_convention_naming(due_date: str, total_amount: float, payable_from: str = None, payable_to: str = None, invoice_number: str = None) -> Union[str, None]:
    try:
        invoice_name = None

        # Check all possible cases and construct the file name based on available features
        if due_date is not None and total_amount is not None:
            invoice_name = f"{due_date} {format_currency(total_amount)} {payable_from or 'Unknown'} {payable_to or 'Unknown'} {invoice_number or 'NoInvoice'}.pdf"
        elif due_date is None and total_amount is not None:
            invoice_name = f"{format_currency(total_amount)} {payable_from or 'Unknown'} {payable_to or 'Unknown'} {invoice_number or 'NoInvoice'}.pdf"
        elif due_date is not None and total_amount is None:
            invoice_name = f"{due_date} {payable_from or 'Unknown'} {payable_to or 'Unknown'} {invoice_number or 'NoInvoice'}.pdf"
        else:
            invoice_name = f"{payable_from or 'Unknown'} {payable_to or 'Unknown'} {invoice_number or 'NoInvoice'}.pdf"

        return invoice_name
    except Exception as e:
        log.error(f"Error creating document name: {str(e)}")
        return None

# Document Splitting Functions
def append_features(dic, current_due_date_converted, current_total_amount, payable_from=None, payable_to=None, invoice_number=None):
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

    dic['payable from'].append(payable_from if payable_from is not None else 'None')
    dic['payable to'].append(payable_to if payable_to is not None else 'None')
    dic['invoice number'].append(invoice_number if invoice_number is not None else 'None')

    return dic

def find_first_non_none(dic):
    # Initialize variables to hold the first non-None values for each feature
    selected_due_date = None
    selected_total_amount = None
    selected_payable_from = None
    selected_payable_to = None
    selected_invoice_number = None
    
    # Iterate over the lists in the dictionary simultaneously
    for due_date, total_amount, payable_from, payable_to, invoice_number in zip(
            dic['due date'], dic['total amount'], dic['payable from'], dic['payable to'], dic['invoice number']):
        
        # Check and assign the first non-None due date
        if due_date != 'None' and selected_due_date is None:
            selected_due_date = due_date
            
        # Check and assign the first non-None total amount
        if total_amount != 'None' and selected_total_amount is None:
            selected_total_amount = total_amount
        
        # Check and assign the first non-None payable from
        if payable_from != 'None' and selected_payable_from is None:
            selected_payable_from = payable_from
        
        # Check and assign the first non-None payable to
        if payable_to != 'None' and selected_payable_to is None:
            selected_payable_to = payable_to
        
        # Check and assign the first non-None invoice number
        if invoice_number != 'None' and selected_invoice_number is None:
            selected_invoice_number = invoice_number
        
        # If all first non-None values are found, exit the loop
        if (selected_due_date is not None and selected_total_amount is not None and
            selected_payable_from is not None and selected_payable_to is not None and
            selected_invoice_number is not None):
            break
            
    # Return the first non-None values for all features
    return selected_due_date, selected_total_amount, selected_payable_from, selected_payable_to, selected_invoice_number

# Create a CSV file containing extracted features and upload it to an S3 bucket.  in review!
def excel_creator(
    s3_client:BaseClient,
    bucket_name: str,
    prefix_splited_doc: str,
    splited_doc_name: str,
    all_excel_data: list,
    header_written: bool,
    prefix_sheet_creator: str,
    due_date: str,
    total_amount: float,
    paybale_from: str,
    paybale_to: str,
    invoice_number: str
) -> None:
    try:
        # Initialize a dictionary to store extracted features information
        extracted_info = {}
        
        extracted_info["Payable From"] = paybale_from
        extracted_info["Due Date"]     = due_date
        extracted_info["Total Amount"] = total_amount
        extracted_info["Payable To"]   = paybale_to
        extracted_info["Invoice Number"]   = invoice_number

        extracted_info["Link to PDF"] = create_preauthenticated_url(s3_client, bucket_name, f"{prefix_splited_doc}/{splited_doc_name}")
        
        # Convert extracted information to a DataFrame
        excel_row_data = pd.DataFrame([extracted_info])
        
        if not header_written:
            # Write header only if it hasn't been written before
            header = list(extracted_info.keys())
            all_excel_data.append(header)
            header_written = True

        # Append the current row of data to the overall Excel data
        all_excel_data.append(excel_row_data)
        
        # Concatenate all data into a single DataFrame
        excel_data_df = pd.concat(all_excel_data, ignore_index=True)
        
        # Create an in-memory buffer to store the Excel file
        excel_buffer = BytesIO()
        
        # Save the DataFrame to the Excel buffer
        excel_data_df.to_excel(excel_buffer, index=False)
        
        # Upload the Excel file to the specified S3 bucket
        s3_client.put_object(
            Bucket=bucket_name,
            Key=prefix_sheet_creator,
            Body=excel_buffer.getvalue()
        )

    except Exception as e:
        # Handle any exceptions that may occur during the process and print an error message
        log.error(f"Error creating Excel file and uploading to S3: {str(e)}")

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


