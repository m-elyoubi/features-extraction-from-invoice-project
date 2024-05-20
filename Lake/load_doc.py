import boto3
from typing import Union
import logging as log



def load_document(s3_bucket: str, s3_client: boto3.client, s3_key: str) -> Union[bytes, None]:
    try:
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        return response['Body'].read()
    except Exception as e:
        log.error(f"Error loading file from S3: {str(e)}")
        return None
