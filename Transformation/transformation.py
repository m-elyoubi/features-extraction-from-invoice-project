from utilities import Scannedpage_tobyte
import fitz
from typing import List, Union


# Transforms a PDF document into a list of images, one per page.
def transformation_document(pdf_content: bytes) -> Union[List[bytes], dict]:
  
    try:
        list_images = []  # Initialize an empty list to store the images
        pdf_document = fitz.open(stream=pdf_content, filetype="pdf")  # Open the PDF document from the byte content
        for i in range(1, len(pdf_document) + 1):  # Iterate through each page in the PDF
            image_content = Scannedpage_tobyte(pdf_content, i)  # Convert the current page to an image
            list_images.append(image_content)  # Append the image content to the list
        return list_images  # Return the list of images
    except Exception as e:
        # If an error occurs, return a dictionary with error details
        return {"Title": "Error converting PDF to images", "error": str(e)}
