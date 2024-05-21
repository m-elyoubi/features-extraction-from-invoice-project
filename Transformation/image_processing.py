
from botocore.client import BaseClient
import cv2 as cv
from Transformation.transformation import transformation_document
from Lake.upload_doc import upload_doc  
from Extract.extraction import extraction_features
from utilities import excel_creator,append_features, name_document_with_convention_naming,find_first_non_none
import numpy as np
import logging as logger


# split document based on extracted features in review!
def process_doc(s3_client: BaseClient,textract_client: BaseClient,bucket_name,prefix_splited_doc: str,doc,prefix_sheet_creator: str) -> None: 
   
    all_csv_data = []       # Initialize an empty list to accumulate CSV data
    header_written = False
    # Initialize variables for reference information
    reference_due_date = None
    reference_total_amount = None
    reference_payabale_to = None
    reference_payabale_from = None
    reference_invoiceNumber = None
    doc_name = None
    
    similar_pages = []
    pdf_index = 1
    temp_pdf_name = None
    

    try:
        # Make inner compraison between images.
            # Todo: Compare the similarity of images. 
            # Todo: Convert Image to pdf document
        content_images_list = transformation_document(doc)
        
        # Create this dictionary to save the first due date and corresponding amount that they come at the top of the document
        dic={
            'due date':[] ,
            'total amount':[],
            'payable from':[],
            'payable to':[],
            'invoice number':[],

            }
        # Iterate over each image content in the array
        for i, content_image in enumerate(content_images_list, start=1):
            # Decode image content and resize if necessary
            img_np = cv.imdecode(np.fromstring(content_image, np.uint8), cv.IMREAD_COLOR)
            

            temp_pdf_name = f"/tmp/pdf_{pdf_index}.pdf" #current_payabale_to     
           
            _,current_due_date_converted, current_total_amount,current_paybale_from, current_paybale_to, current_invoiceNumber  = extraction_features(textract_client,content_image)  # thi will give us the four wanted features from each image
           
            if reference_total_amount is not None or reference_due_date is not None:
              

                # Check if the page is similar to the previous one based on SSIM or extracted information
                if (current_total_amount == reference_total_amount or current_due_date_converted==reference_due_date):
                    #"Page {i} is similar to the previous page. Adding to the current sequence."
                    append_features(dic,reference_due_date,reference_total_amount,reference_payabale_from,reference_payabale_to,reference_invoiceNumber)
                    similar_pages.append(img_np)
        
                else:
                    # Pages are not similar, save the current sequence to a new PDF
                    if similar_pages:
                        
                        # add for each splited document with own due date and total amount
                        append_features(dic,reference_due_date,reference_total_amount,reference_payabale_from,reference_payabale_to,reference_invoiceNumber)
                       
                        selected_due_date, selected_total_amount,selected_payabale_from,selected_payabale_to,selected_invoiceNumber= find_first_non_none(dic)
                        
                        doc_name =name_document_with_convention_naming(selected_due_date, selected_total_amount,selected_payabale_from,selected_payabale_to,selected_invoiceNumber)
                        upload_doc(s3_client,similar_pages, bucket_name, prefix_splited_doc, doc_name, temp_pdf_name)
                
                        excel_creator(s3_client,bucket_name,prefix_splited_doc, doc_name, all_csv_data,header_written, prefix_sheet_creator,selected_due_date, selected_payabale_from,selected_payabale_to,selected_invoiceNumber)                                  
                        header_written=True
                        


                        dic['due date']=[]
                        dic['total amount']=[]
                        dic['payable from']=[]
                        dic['payable to']=[]
                        dic['invoice number']=[]
                        
                    
                    pdf_index += 1
                    # Start a new sequence with the current page
                    similar_pages = [img_np]
            else:
                similar_pages.append(img_np)  

            
            reference_payabale_to = current_paybale_to
            reference_due_date= current_due_date_converted
            reference_total_amount = current_total_amount
            reference_payabale_from = current_paybale_from
            reference_payabale_from = current_invoiceNumber


        # Save the last sequence to a new PDF if not empty
        if similar_pages:
            temp_pdf_name = f"/tmp/pdf_{pdf_index}.pdf"
            selected_due_date, selected_total_amount=find_first_non_none(dic)
            doc_name =name_document_with_convention_naming(selected_due_date, selected_total_amount)
            upload_doc(s3_client,similar_pages, bucket_name, prefix_splited_doc, doc_name, temp_pdf_name)
            excel_creator(s3_client,bucket_name,prefix_splited_doc, doc_name, all_csv_data,header_written, prefix_sheet_creator,selected_due_date, selected_total_amount,selected_payabale_from,selected_payabale_to,selected_invoiceNumber)
            

    except Exception as e:
        logger.error(f"Error splitting document: {str(e)}")
    return None
