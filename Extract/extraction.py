import concurrent.futures
from utilities import image_to_text, extract_due_date, extract_total_amount, extract_payable_from, extract_payable_to,extract_InvoiceNumber
from typing import Tuple, Union
from botocore.client import BaseClient
import logging as logger

# this funtion used to extract features required 
def extraction_features(textract_client: BaseClient, content_image: bytes) -> Tuple[Union[str, None], Union[str, None], Union[float, None], Union[str, None], Union[str, None]]:
    try:
        # Extract text from the image using the Textract client
        text = image_to_text(textract_client, content_image)
        
        # Use ThreadPoolExecutor to run multiple functions concurrently for efficiency
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Submit each extraction function to the executor
            future_payable_from = executor.submit(extract_payable_from, text)
            future_due_date = executor.submit(extract_due_date, text)
            future_total_amount = executor.submit(extract_total_amount, text)
            future_payable_to = executor.submit(extract_payable_to, text)
            future_invoice_number = executor.submit(extract_InvoiceNumber, text)

            # Retrieve results from each future
            payable_from = future_payable_from.result()
            due_date, due_date_converted = future_due_date.result()
            total_amount = future_total_amount.result()
            payable_to = future_payable_to.result()
            invoice_number = future_invoice_number.result()

            # Log the extracted features for debugging purposes
            logger.info(f'{due_date},{due_date_converted} ,{total_amount} , {payable_from}, {payable_to},{invoice_number}')
    
            # Return the extracted features as a tuple
            return due_date, due_date_converted, total_amount, payable_from, payable_to, invoice_number

    except Exception as e:
        # Log any exceptions that occur during the extraction process
        logger.error(f'There is an error in extraction features: {e}')
        return None, None, None, None, None, None