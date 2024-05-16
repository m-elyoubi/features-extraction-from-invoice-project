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
############################### extraction Features Funtions #######################

def extract_due_date(text: str)-> str:
    return 0



def extract_total_amount(text: str)-> str:
    return 0



def extract_payable_from(text: str)-> str:

    return 0



def extract_payable_to(text: str)-> str:

    return 0



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
                            #       Section D: Main Feature Extraction functions    #
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


def Upload_doc()-> None:

    try:
        # put Process logic here

    except Exception as e:
        logger.error(f"Error Upload Document to S3 Bucket: {str(e)}")


# Process document
def Process_doc()-> None:


    try:

        
    except Exception e:

        logger.error(f"Error process Document : {str(e)}")



def sheet_creator(
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


    try:


    
    except Exception e:
        
        # Handle any exceptions that may occur during the process and print an error message
        logging.error(f"Error creating Sheet file and uploading to S3: {str(e)}")
        return None



                            #########################################################
                            #                                                       #
                            #         Section E: main handler funtion               #
                            #                                                       #
                            #########################################################

def lambda_handler():

    
    return {
        'statusCode':200,
        'body':'everthing was going successfully'
    }
