from utilities import save_images_to_pdf
import cv2 as cv
import logging as log
from botocore.client import BaseClient


# Upload a document to an S3 bucket with convention naming. in review!
def upload_doc(
    s3_client: BaseClient,
    np_array: list,
    bucket_name: str,
    prefix_splited_doc: str,
    doc_name: str,
    temp_pdf_name: str
    ) -> None:

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
        save_images_to_pdf(image_paths, temp_pdf_name)

        # Define the destination key for the PDF in S3
        doc_output_key = f"{prefix_splited_doc}/{doc_name}"

        # Upload the generated PDF to S3
        with open(temp_pdf_name, 'rb') as pdf_file:
            s3_client.upload_fileobj(pdf_file, bucket_name, doc_output_key)

        # Print a message indicating successful upload to S3
        log.info(f"Uploaded PDF to S3: s3://{bucket_name}/{doc_output_key}")

    except Exception as e:
        # Handle any exceptions that may occur during the process and print an error message
        log.error(f"Error saving images to PDF and uploading to S3: {str(e)}")
