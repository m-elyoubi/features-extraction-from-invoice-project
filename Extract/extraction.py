import concurrent.futures
from utilities import image_to_text, detect_due_date, detect_total_amount, detect_payable_from, detect_payable_to
from typing import Tuple, Union
from botocore.client import BaseClient
import logging as logger

def extraction_totalamount_duedate_sender_receiver(textract_client: BaseClient, content_image: bytes) -> Tuple[Union[str, None], Union[str, None], Union[float, None], Union[str, None], Union[str, None]]:
    
    try:
        text = image_to_text(textract_client, content_image)
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_payable_from = executor.submit(detect_payable_from, text)
            future_due_date = executor.submit(detect_due_date, text)
            future_total_amount = executor.submit(detect_total_amount, text)
            future_payable_to = executor.submit(detect_payable_to, text)

            payable_from = future_payable_from.result()
            due_date, due_date_converted = future_due_date.result()
            total_amount = future_total_amount.result()
            payable_to = future_payable_to.result()

            logger.info(f'{due_date},{due_date_converted} ,{total_amount} , {payable_from}, {payable_to}')
    
            return due_date, due_date_converted, total_amount, payable_from, payable_to

    except Exception as e:
        logger.error(f'there is error in extraction features {e}')