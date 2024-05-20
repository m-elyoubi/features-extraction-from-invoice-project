
from botocore.client import BaseClient
import cv2 as cv
from Transformation.transformation import transformation_document
from Lake.upload_doc import upload_document
from utilities import sheet_creator,append_due_date_and_amount, name_document_with_convention_naming,find_first_non_none
import numpy as np
import logging as logger



def process_doc(s3_client: BaseClient, textract_client: BaseClient, bucket_name: str, prefix_splited_doc: str, doc: bytes, all_csv_data: list, prefix_sheet_creator: str, header_written: bool) -> None:
    reference_due_date = None
    reference_total_amount = None
    reference_payable_to = None
    reference_payable_from = None
    doc_name = None
    similar_pages = []
    pdf_index = 1
    temp_pdf_name = None
    dic = {'due date': [], 'total amount': []}
    try:
        content_images_list = transformation_document(doc)
        for i, content_image in enumerate(content_images_list, start=1):
            img_np = cv.imdecode(np.frombuffer(content_image, np.uint8), cv.IMREAD_COLOR)
            temp_pdf_name = f"/tmp/pdf_{pdf_index}.pdf"
            _, current_due_date_converted, current_total_amount, current_payable_from, current_payable_to = extraction_totalamount_duedate_sender_receiver(textract_client, content_image)
           
            if reference_total_amount is not None or reference_due_date is not None:
                if (current_total_amount == reference_total_amount or current_due_date_converted == reference_due_date):
                    append_due_date_and_amount(dic, reference_due_date, reference_total_amount)
                    similar_pages.append(img_np)
                else:
                    if similar_pages:
                        append_due_date_and_amount(dic, reference_due_date, reference_total_amount)
                        selected_due_date, selected_total_amount = find_first_non_none(dic)
                        doc_name = name_document_with_convention_naming(selected_due_date, selected_total_amount)
                        upload_document(s3_client, similar_pages, bucket_name, prefix_splited_doc, doc_name, temp_pdf_name)
                        sheet_creator(s3_client, bucket_name, prefix_splited_doc, doc_name, all_csv_data, header_written, prefix_sheet_creator, selected_due_date, selected_total_amount, reference_payable_from, reference_payable_to)                                  
                        header_written = True
                        dic['due date'] = []
                        dic['total amount'] = []
                    pdf_index += 1
                    similar_pages = [img_np]
            else:
                similar_pages.append(img_np)

            reference_payable_to = current_payable_to
            reference_due_date = current_due_date_converted
            reference_total_amount = current_total_amount
            reference_payable_from = current_payable_from

        if similar_pages:
            temp_pdf_name = f"/tmp/pdf_{pdf_index}.pdf"
            selected_due_date, selected_total_amount = find_first_non_none(dic)
            doc_name = name_document_with_convention_naming(selected_due_date, selected_total_amount)
            upload_document(s3_client, similar_pages, bucket_name, prefix_splited_doc, doc_name, temp_pdf_name)
            sheet_creator(s3_client, bucket_name, prefix_splited_doc, doc_name, all_csv_data, header_written, prefix_sheet_creator, selected_due_date, selected_total_amount, reference_payable_from, reference_payable_to)
    except Exception as e:
        logger.error(f"Error splitting document: {str(e)}")
    return None
