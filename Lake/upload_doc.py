from utilities import images_to_pdf
import cv2 as cv
import logging as log
from botocore.client import BaseClient


def upload_document(s3_client: BaseClient, np_array: list, bucket_name: str, prefix_splited_doc: str, doc_name: str, temp_pdf_name: str) -> None:
    try:
        image_paths = []
        for i, np_img in enumerate(np_array):
            cv_img_temp = cv.cvtColor(np_img, cv.COLOR_RGB2BGR)
            _, img_bytes = cv.imencode('.jpg', cv_img_temp)
            temp_img_path = f"/tmp/image_{i}.jpg"
            with open(temp_img_path, 'wb') as f:
                f.write(img_bytes)
            image_paths.append(temp_img_path)

        images_to_pdf(image_paths, temp_pdf_name)
        doc_output_key = f"{prefix_splited_doc}/{doc_name}"

        with open(temp_pdf_name, 'rb') as pdf_file:
            s3_client.upload_fileobj(pdf_file, bucket_name, doc_output_key)
        log.info(f"Uploaded PDF to S3: s3://{bucket_name}/{doc_output_key}")
    except Exception as e:
        log.error(f"Error saving images to PDF and uploading to S3: {str(e)}")