import os
import io
import zipfile
from datetime import datetime
from typing import List

import boto3


def compress_file(file_path: str, output_zip: str) -> None:
    """
    Compress a file into a zip archive.

    :param file_path: Path to the file to be compressed.
    :param output_zip: Path to the output zip file.
    """
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(file_path, os.path.basename(file_path))


def save_in_s3(local_path: str, path_s3: str, file_type: str) -> None:
    """
    Save a file to an S3 bucket.

    :param local_path: Path to the local file.
    :param path_s3: Path within the S3 bucket.
    :param file_type: Type of the file (xml, zip, csv).
    """
    s3_client = boto3.client('s3')
    bucket_name = 'tr-risk-data-prd'
    today = datetime.today()
    s3_object_name = f"risk_write/mr/irrbb-reports/generation_date_{today.strftime('%Y_%m_%d')}/{path_s3}"

    try:
        if file_type == 'xml':
            content_type = 'application/xml'
            with open(local_path, 'r') as file:
                file_body = file.read()

        elif file_type == 'zip':
            content_type = 'application/zip'
            with open(local_path, 'rb') as file:
                zip_buffer = io.BytesIO(file.read())
            file_body = zip_buffer.getvalue()

        elif file_type == 'csv':
            content_type = 'text/csv'
            with open(local_path, 'rb') as file:
                file_body = file.read()

        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_object_name,
            Body=file_body,
            ContentType=content_type
        )
        print(f"File uploaded to s3://{bucket_name}/{s3_object_name}")

    except Exception as e:
        print(f"Error uploading file to S3: {e}")


def combine_report_flags(report_list: List[List[str]]) -> List[List[str]]:
    """
    Combine report flags, ensuring each report has the highest-priority flag.

    :param report_list: List of [report, flag] pairs.
    :return: Combined list of [report, flag] pairs.
    """
    combined_reports = {}

    for report, flag in report_list:
        if report not in combined_reports or flag == 'true':
            combined_reports[report] = flag

    result = [[report, flag] for report, flag in combined_reports.items()]
    result.sort(key=lambda x: x[0])

    return result
