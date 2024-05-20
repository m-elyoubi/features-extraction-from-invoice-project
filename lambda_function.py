import os
import logging as log
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


def handler(event, context):


    all_csv_data = []
    header_written = False

    try:
        for record in event['Records']:
            bucket_name = record['s3']['bucket']['name']
            doc_key = record['s3']['object']['key']
            doc_content = load_document(bucket_name, s3_client, doc_key)

            if doc_key.lower().endswith('.pdf'):
                doc_name = os.path.basename(doc_key).replace(".pdf", "")
                prefix_splited_doc = f"{splited_doc_folder}{doc_name}"
                prefix_sheet_creator = f"{output_folder}{doc_name}.csv"
                process_doc(s3_client, textract_client, bucket_name, prefix_splited_doc, doc_content, all_csv_data, prefix_sheet_creator, header_written)

    except Exception as e:
        log.error(f"Error handling event: {str(e)}")

    return {
        'statusCode': 200,
        'body': 'Textract jobs completed for all PDFs in the input bucket.'
    }