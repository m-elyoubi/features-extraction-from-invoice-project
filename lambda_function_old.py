# Import Libraries 
import fitz
from io import BytesIO
from PIL import Image
import boto3
import locale   # This library is to manager special characters/symbols (ex: $,...)
from datetime import datetime
from dateutil import parser
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

################### define Logging for traking events ######
logging.basicConfig(level=logging.DEBUG)
loger = logging.getLogger('Log')




#################################################
#              Generic Functions                #
# ###############################################

# The pre-signed URL grants temporary access to download the specified splited document from the S3 bucket. in review
def generate_presigned_url(bucket_name: str, object_key: str, expiration=3600)-> Union[str,None]:
    
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
        logging.info(f"Error generating pre-signed URL: {e}")
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
        logging.error(f"Error extracting text from image: {str(e)}")
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
def convert_date(input_date: str)-> str:
    
    # Convert string to datetime object
    date_object = datetime.strptime(input_date, "%Y-%m-%d")

    # Format the datetime object as ymd (year-month-day without separators)
    output_format = date_object.strftime("%y%m%d")
    return output_format
# logging.info(f'convert_date:{convert_date("2024-04-30")}') #tested done!

# Function to convert string to float based on condition - 
#   Todo: Manage all position of dollar symbole in the following scenario : ex : $ 6,66 , 56,66.00$  in review!
def convert_to_float(amount_str: str) -> float:
    
    try:
        amount_str = amount_str.replace(' ', '')
        # Remove dollar sign if present
        if amount_str.startswith('$'):
            amount_str = amount_str[1:]
        if amount_str.endswith('$'):
            amount_str = amount_str[:-1]

        # Remove commas and spaces
        amount_str = amount_str.replace(',', '')

        # Convert the string to a float
        amount_float = float(amount_str)

        # Log successful conversion
        logging.info(f"Successfully converted '{amount_str}' to float: {amount_float}")
        return amount_float

    except ValueError as e:
        # Handle the case where the conversion fails due to invalid input
        logging.error(f"Error converting '{amount_str}' to float: {e}")
        return None
# logging.info(f'convert_to_float:{convert_to_float("$ 6,66")}') #tested done!

# Parse a date string using multiple date formats and return the parsed date in a standardized format - Done!
def parse_date(date_str: str) -> str:
    
    formats = ["%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y", "%B %d, %Y", "%B %d,%Y"]  # List of accepted date formats

    if date_str:  # Check if the input date string is not empty
        for date_format in formats:
            try:
                # Attempt to parse the date using the current format
                parsed_date = datetime.strptime(date_str, date_format)
                formatted_date = parsed_date.strftime("%Y-%m-%d")
                logging.info(f"Successfully parsed '{date_str}' to '{formatted_date}' using format '{date_format}'")
                return formatted_date  # Return the formatted date
            except ValueError as e:
                logging.debug(f"Failed to parse '{date_str}' using format '{date_format}': {e}")
                pass

    logging.warning(f"Unable to parse date string '{date_str}' using any of the specified formats")
    return None  # Return None if the date string cannot be parsed using any of the specified formats

#Save a list of images into a single PDF file  in review !
def images_to_pdf(image_paths :list, output_pdf_path : str):
    
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
        logging.info(f"PDF successfully generated and saved to '{output_pdf_path}'")
    except Exception as e:
        # Handle any exceptions that may occur during the process and print an error message
        return (f"Error saving images to PDF: {str(e)}")


#################################################
#              Relative Functions               #
# ###############################################

# Convert a specific page of a PDF document to image content.   Done!!
def convert_page_to_image_content(doc_content: bytes, page_number: int) -> bytes:
    
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

# Transform Loaded PDF file into Image. Done!!
def Transformation_document(pdf_content) -> list:
    try:
        list_images = []    # List of converted pdf pages to images

        # Loop through all pages of the pdf and convert them into images
        for i in range(1, len(fitz.open(stream=pdf_content, filetype="pdf")) + 1):
            image_content = convert_page_to_image_content(pdf_content, i)
            list_images.append(image_content)

        return list_images

    except Exception as e:
        return { 
            "Title": "Error converting PDF to images" ,
            "error": "{}".format(str(e))
        }

# Finds the first non-'None' values for 'due date' and 'total amount' in the given dictionary if all elements none it would take None in review
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
    
#  add the given dictionary with current due date and total amount in review
def append_due_date_and_amount(dic,current_due_date_converted,current_total_amount):

    if current_due_date_converted is None and current_total_amount is None:
        # Add current due date and current total amount to the dictionary
        dic['due date'].append('None')
        dic['total amount'].append('None')
    elif  current_due_date_converted is None:
        dic['due date'].append('None')
        dic['total amount'].append(current_total_amount)
    else:
        dic['due date'].append(current_due_date_converted)
        dic['total amount'].append("None")
            
            
    # Add current due date and current total amount to the dictionary
    dic['due date'].append(current_due_date_converted)
    dic['total amount'].append(current_total_amount)

    return dic

#   Restruct the function based on  return filter in review
def correct_customer_name(sentence:str)-> str:
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
#       Section 1: Feature Extraction functions         #
#                                                       #
#########################################################

#   Fct 1: Sub function to get due_date feature  - Done! 
def detect_due_date(text: str) -> tuple:
    
    try:
        formatted_date = None

        # Regular expression pattern to match dates
        all_date_pattern = re.compile(r'\b(?:\d{1,2}[/]\d{1,2}[/]\d{2,4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)\s\d{1,2},?\s?\d{2,4})\b', flags=re.IGNORECASE)
        
        # Search for due date pattern in the text
        due_date_match = re.search(r'\b(?:bill date|payment due date|total amount due|due date):?\s*(\d{1,2}[/]\d{1,2}[/]\d{2,4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)\s\d{1,2},?\s?\d{2,4})\b', text.lower(), flags=re.IGNORECASE)

        if due_date_match:
            # Extract the due date from the match
            extracted_date = due_date_match.group(1)
            logging.debug(f'This is the extracted Date: {extracted_date}')
            
            # Convert the extracted date to YYYY-MM-DD format
            formatted_date = datetime.strptime(extracted_date, "%m/%d/%Y").strftime("%Y-%m-%d")
            
            # Convert the formatted date to YYMMDD format
            formatted_date_convert = convert_date(formatted_date) if formatted_date else None
            
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
                formatted_date_convert = convert_date(date) if date else None
                return (formatted_date, formatted_date_convert)
        else:
            return (None, None)

    except Exception as e:
        logging.error(f"Error detecting due date: {str(e)}")
        return (None, None)


#   Fct 2: Sub function to get totale amount  - Done! 
def detect_total_amount(text: str)-> Union[float,None]:
        
    singaltotal_amount_pattern = r"balance due\s*?\$([\d,]+.\d{2})|total amount due\s+\d{2}/\d{2}/\d{4}\s+\$([\d.]+)|total payment due\n?.*?\n?([\d,]+\.\d+)|total due\s*\$([\d.]+)|amount due\s*([\d,.]+)|auto pay:?\s*\$([\d,.]+)|total amount due\s*.*?\n.*?\n\s*\$([\d.]+)|invoice amount\s*?\$([\d,]+.\d{2})"
    all_amount_pattern = re.compile(r'\$(\s*[0-9,]+(?:\.[0-9]{2})?)')
   
    # Search for all the amount in the text
    all_amount_match = all_amount_pattern.search(text.lower())
    # Search for only the total amount in the text   
    match = re.search(singaltotal_amount_pattern, text.lower(), re.DOTALL)

    # Check if a match is found
    if match:
        balance_due = next((x for x in match.groups() if x is not None), None) if match else None
        loger.info(f'The balence due exsit and it is : {balance_due}')
        return convert_to_float(balance_due)

    elif all_amount_match:
       extracted_amount = all_amount_match.group(1)
       return  convert_to_float(extracted_amount)
    
    else:
        return None
#   Fct 3: Sub function to get paybale to feature in progress
def detect_payable_to(text: str)-> Union[str,None]: 
    return 0

#   Fct 4: Sub function to get paybale feature in review! Try to cover all scenarios (\t, \n, ...)

def detect_payable_from(text: str)-> Union[str,None]:
    
    customer_name_match1 = re.search(r'billed to:?\n?(.*)|from:\n?(.*)|bill to:?\n?(.*)|site name:?\n?(.*)|(.*)\npo box 853|(.+?)\n(.+?)\n(.+?)p\.o\. box 853|((?:.*\n){3})(po|p.o|p.o.)\s*(box|box) 853|client name:?\s*(.*)',text.lower())

    if customer_name_match1 is not None :
        x=next((x for x in customer_name_match1.groups() if x is not None), "default") 
        # if customer_name_match1 and customer_name_match1.group(1).strip()!= "":
        # print(f'customer_name before:{x}')
        customer_name = ' '.join(re.findall(r'\b[A-Z][A-Z\s]+\b', x))

        if len(customer_name)>3:
            c=  customer_name
        else:
            c=  x
        return  correct_customer_name(c)
                            
    else:
        return None


#   Fct 5: name file based on whatever detected features in {Feat.2} {$Feat.1} {Feat.3} {Feat.4 }.pdf format in review
def name_document_with_convention_naming(due_date: str, total_amount: float) -> Union[str, None]:
    
    try:
        invoice_name = None  

        # Check all possible cases
        if due_date is not None  and total_amount is not None:
            # Create a destination name with due_date, formatted total amount
            invoice_name = f"{due_date} {format_currency(total_amount)}.pdf"
        elif due_date is None and total_amount is not None:
            # Create a destination name with formatted total amount
            invoice_name = f"{format_currency(total_amount)} .pdf"
        else:
            # Create a destination name with due_date
            invoice_name = f"{due_date} .pdf"

        return invoice_name
    except Exception as e:
        logging.error(f"Error creating document name: {str(e)}")
        return None

    

#########################################################
#                                                       #
#       Section 2: Detect the list of extracted Items   #
#                                                       #
#########################################################

# Load pdf file from s3 bucket   In Done!
def Load_document(s3_bucket: str, s3_client: BaseClient, s3_key: str) -> Union[bytes, None]:
  
    try:
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        return response['Body'].read()

    except Exception as e:
        logging.error(f"Error loading file from S3: {str(e)}")
        return None


# Detect total amount (feat1), due date(feat 2), sender (feat3) and Receiver(feat4)  in review
def extraction_totalamount_duedate_sender_Receiver(textract_client: BaseClient, content_image: bytes) -> tuple:
    # Convert Image to text
    text = image_to_text(textract_client, content_image)
    
    # Create a ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit the tasks for parallel execution
        future_payable_from = executor.submit(detect_payable_from, text)
        future_due_date = executor.submit(detect_due_date, text)
        future_total_amount = executor.submit(detect_total_amount, text)
        future_payable_to = executor.submit(detect_payable_to, text)

        # Get results from the futures
        paybale_from = future_payable_from.result()
        due_date, due_date_converted = future_due_date.result()
        total_amount = future_total_amount.result()
        paybale_to = future_payable_to.result()

    # Return a tuple containing the due date and total payment
    return  (due_date,due_date_converted, total_amount ,paybale_from, paybale_to)

# split document based on extracted features in review!
def split_document(s3_client: BaseClient,textract_client: BaseClient,bucket_name,prefix_splited_doc: str,doc,all_csv_data: list,prefix_sheet_creator: str,header_written:bool) -> None: 
   
    # Initialize variables for reference information
    reference_due_date = None
    reference_total_amount = None
    reference_payabale_to = None
    reference_payabale_from = None
    doc_name = None
    


    similar_pages = []
    pdf_index = 1
    temp_pdf_name = None
    

    try:
        # Make inner compraison between images.
            # Todo: Compare the similarity of images. 
            # Todo: Convert Image to pdf document
        content_images_list = Transformation_document(doc)
        
        # Create this dictionary to save the first due date and corresponding amount that they come at the top of the document
        dic={'due date':[] ,'total amount':[]}
        # Iterate over each image content in the array
        for i, content_image in enumerate(content_images_list, start=1):
            # Decode image content and resize if necessary
            img_np = cv.imdecode(np.fromstring(content_image, np.uint8), cv.IMREAD_COLOR)
            

            temp_pdf_name = f"/tmp/pdf_{pdf_index}.pdf" #current_payabale_to
           
            _,current_due_date_converted, current_total_amount,current_paybale_from, current_paybale_to  = extraction_totalamount_duedate_sender_Receiver(textract_client,content_image)  # thi will give us the four wanted features from each image
           
            if reference_total_amount is not None or reference_due_date is not None:
              

                # Check if the page is similar to the previous one based on SSIM or extracted information
                if (current_total_amount == reference_total_amount or current_due_date_converted==reference_due_date):
                    #"Page {i} is similar to the previous page. Adding to the current sequence."
                    append_due_date_and_amount(dic,reference_due_date,reference_total_amount)
                    similar_pages.append(img_np)
        
                else:
                    # Pages are not similar, save the current sequence to a new PDF
                    if similar_pages:
                        
                        # add for each splited document with own due date and total amount
                        append_due_date_and_amount(dic,reference_due_date,reference_total_amount)
                       
                        selected_due_date, selected_total_amount=find_first_non_none(dic)
                        
                        doc_name =name_document_with_convention_naming(selected_due_date, selected_total_amount)
                        upload_document(s3_client,similar_pages, bucket_name, prefix_splited_doc, doc_name, temp_pdf_name)
                
                        sheet_creator_new(s3_client,bucket_name,prefix_splited_doc, doc_name, all_csv_data,header_written, prefix_sheet_creator,selected_due_date, selected_total_amount,reference_payabale_from, reference_payabale_to)                                  
                        header_written=True
                        


                        dic['due date']=[]
                        dic['total amount']=[]
                    
                    pdf_index += 1
                    # Start a new sequence with the current page
                    similar_pages = [img_np]
            else:
                similar_pages.append(img_np)

            
            reference_payabale_to = current_paybale_to
            reference_due_date= current_due_date_converted
            reference_total_amount = current_total_amount
            reference_payabale_from = current_paybale_from


            
            

        # Save the last sequence to a new PDF if not empty
        if similar_pages:
            temp_pdf_name = f"/tmp/pdf_{pdf_index}.pdf"
            selected_due_date, selected_total_amount=find_first_non_none(dic)
            doc_name =name_document_with_convention_naming(selected_due_date, selected_total_amount)
            upload_document(s3_client,similar_pages, bucket_name, prefix_splited_doc, doc_name, temp_pdf_name)
            sheet_creator_new(s3_client,bucket_name,prefix_splited_doc, doc_name, all_csv_data,header_written, prefix_sheet_creator,selected_due_date, selected_total_amount,reference_payabale_from,reference_payabale_to)
            

    except Exception as e:
        logging.error(f"Error splitting document: {str(e)}")
    return None

# Upload a document to an S3 bucket with convention naming. in review!

def upload_document(s3_client: BaseClient, np_array: list, bucket_name: str, prefix_splited_doc: str, doc_name: str, temp_pdf_name: str) -> None:

    try:
        # Initialize an empty list to store file paths of temporary images
        image_paths = []

        # Loop through each image in the NumPy array
        for i, np_img in enumerate(np_array):
            # Convert NumPy image to OpenCV format (BGR)
            cv_img_temp = cv.cvtColor(np_img, cv.COLOR_RGB2BGR)

            # Encode the OpenCV image to JPEG format
            _, img_bytes = cv.imencode('.jpg', cv_img_temp)

            # Create a temporary file path for the current image
            temp_img_path = f"/tmp/image_{i}.jpg"

            # Write the image bytes to the temporary file
            with open(temp_img_path, 'wb') as f:
                f.write(img_bytes)

            # Add the temporary image path to the list
            image_paths.append(temp_img_path)

        # Call the save_images_to_pdf function to generate the PDF using the temporary image paths
        images_to_pdf(image_paths, temp_pdf_name)

        # Define the destination key for the PDF in S3
        doc_output_key = f"{prefix_splited_doc}/{doc_name}"

        # Upload the generated PDF to S3
        with open(temp_pdf_name, 'rb') as pdf_file:
            s3_client.upload_fileobj(pdf_file, bucket_name, doc_output_key)

        # Print a message indicating successful upload to S3
        logging.info(f"Uploaded PDF to S3: s3://{bucket_name}/{doc_output_key}")

    except Exception as e:
        # Handle any exceptions that may occur during the process and print an error message
        logging.error(f"Error saving images to PDF and uploading to S3: {str(e)}")

# Create a CSV file containing extracted features and upload it to an S3 bucket.  in review!

def sheet_creator_new(
    s3_client: BaseClient,
    bucket_name: str,
    prefix_splited_doc: str,
    splited_doc_name: str,
    all_csv_data: list,
    header_written: bool,
    prefix_sheet_creator: str,
    due_date: str,
    total_amount: float,
    paybale_from: str,
    paybale_to: str
) -> None:
   
    # This function is for saving features inside a CSV file.
    # Todo: the stored features should be a list of extracted features in function extraction_()
    # Todo: Upload the excel file in the S3 bucket.
    try:
        # Initialize a dictionary to store extracted features information
        extracted_info = {}
        
        extracted_info["Payable From"] = paybale_from
        extracted_info["Due Date"]     = due_date
        extracted_info["Total Amount"] = total_amount
        extracted_info["Payable To"]   = paybale_to

        # extracted_info["Link to PDF"] = f'https://{bucket_name}.s3.amazonaws.com/{prefix_splited_doc}/{splited_doc_name}'
        extracted_info["Link to PDF"] = generate_presigned_url(s3_client,bucket_name, f"{prefix_splited_doc}/{splited_doc_name}")
        # Convert extracted information to a list for the CSV
        csv_data = list(extracted_info.values())
        
        if not header_written:
            # Write header only if it hasn't been written before
            header = list(extracted_info.keys())
            all_csv_data.append(header)
            header_written = True

        # Append the current row of data to the overall CSV data
        all_csv_data.append(csv_data)
        
        # Save data to a single CSV file
        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerows(all_csv_data)

        # Upload the CSV file to the specified S3 bucket
        s3_client.put_object(
            Bucket=bucket_name,
            Key=prefix_sheet_creator,
            Body=csv_buffer.getvalue()
        )

    except Exception as e:
        # Handle any exceptions that may occur during the process and print an error message
        logging.error(f"Error creating CSV file and uploading to S3: {str(e)}")
        return None



#########################################################
#                                                       #
#       Section 3: main handler funtion                 #
#                                                       #
#########################################################


def handler(event,context):
    
    #-----------------------    Define variables   --------------------- 
    # Initialize AWS clients
    s3_client = boto3.client('s3')  # S3 client
    textract_client = boto3.client('textract')  # Textract client

    splited_doc_folder = os.environ.get('SPLITED_DOC_FOLDER')
    output_folder = os.environ.get('OUTPUT_FOLDER')
  

    all_csv_data = []       # Initialize an empty list to accumulate CSV data
    header_written = False
    
    try: 
        for record in event['Records']:
            # Retrieve bucket name and object key
            bucket_name = record['s3']['bucket']['name']
            doc_key = record['s3']['object']['key']
        
            # Called function 'Load_document' to load document from s3.
            doc_content = Load_document(bucket_name,s3_client, doc_key)
                
            # Check if the object is a PDF file
            if doc_key.lower().endswith('.pdf'):
                doc_name=os.path.basename(doc_key).replace(".pdf", "")
                # prefix_splited_doc has the same name of the document.
                prefix_splited_doc = "{}{}".format(splited_doc_folder,doc_name)
                # sheet_creator has the same name of the document with format csv.
                prefix_sheet_creator="{}{}".format(output_folder,f"{doc_name}.csv")
                # Called function 'split_document' to split document based on extrected features
                split_document(s3_client,textract_client,bucket_name,prefix_splited_doc,doc_content,all_csv_data,prefix_sheet_creator,header_written)   
                
    except Exception as e:
        logging.error(f"Error handling event: {str(e)}")

    return {
        'statusCode': 200,
        'body': 'Textract jobs completed for all PDFs in the input bucket.'
    }