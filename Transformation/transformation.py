from utilities import convert_page_to_image_content
import fitz
from typing import List, Union

def transformation_document(pdf_content: bytes) -> Union[List[bytes], dict]:
    try:
        list_images = []
        pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
        for i in range(1, len(pdf_document) + 1):
            image_content = convert_page_to_image_content(pdf_content, i)
            list_images.append(image_content)
        return list_images
    except Exception as e:
        return {"Title": "Error converting PDF to images", "error": str(e)}
