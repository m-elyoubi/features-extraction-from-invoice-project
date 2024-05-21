import os
import logging as logger
import boto3
from Lake.load_doc import load_document
from Transformation.image_processing import process_doc

                            #########################################################
                            #                                                       #
                            #          Section B: Define Variables                  #
                            #                                                       #
                            #########################################################

#----------- Logging is used for traking events that occur while the program is running -------
# Initialize AWS clients
s3_client = boto3.client('s3')  # S3 client
textract_client = boto3.client('textract')  # Textract client
splited_doc_folder = os.environ.get('FOLDER_SPLITED_DOC')
output_folder = os.environ.get('FOLDER_Sheet_OUTPUT')


def handler(event,context): 

    
    
    try: 
        for record in event['Records']:
            # Retrieve bucket name and object key
            bucket_name = record['s3']['bucket']['name']
            doc_key = record['s3']['object']['key']
        
            # Called function 'Load_document' to load document from s3.
            doc_content = load_document(bucket_name,s3_client, doc_key)
            logger.info(f"load doc: {doc_content}")
            # Check if the object is a PDF file
            if doc_key.lower().endswith('.pdf'):
                doc_name=os.path.basename(doc_key).replace(".pdf", "")
                # prefix_splited_doc has the same name of the document.
                prefix_splited_doc = "{}{}".format(splited_doc_folder,doc_name)
                # sheet_creator has the same name of the document with format csv.
                prefix_sheet_creator="{}{}".format(output_folder,f"{doc_name}.xlsx")
                # Called function 'split_document' to split document based on extrected features
                process_doc(s3_client,textract_client,bucket_name,prefix_splited_doc,doc_content,prefix_sheet_creator)   
                
    except Exception as e:
        logger.error(f"Error handling event: {str(e)}")

    return {
        'statusCode': 200,
        'body': 'Textract jobs completed for all PDFs in the input bucket.'
    }