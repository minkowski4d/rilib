#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import boto3
import io
import sys
import getpass as _getpass
user_name = _getpass.getuser()


def save_in_s3(local_path: str, path_s3: str, file_name: str, file_type: str) -> None:
    """
    Save a file to an S3 bucket.

    :param local_path: Path to the local file.
    :param path_s3: Path within the S3 bucket.
    :param s3_folder_name: Type of the file (xml, zip, csv, parquet)
    :param file_type: Type of the file (xml, zip, csv, parquet).
    """

    s3_client = boto3.client('s3')
    bucket_name = 'tr-risk-data-prd'
    s3_object_name = f"{path_s3}/{file_name}"

    print(f"\t\t Initialising Upload to s3://{bucket_name}/{s3_object_name}")

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

        elif file_type == 'parquet':
            content_type = 'application/octet-stream'
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
        print(f"\t\t File uploaded to s3://{bucket_name}/{s3_object_name}")

    except Exception as e:
        print(f"Error uploading file to S3: {e}")



def save_in_s3_local(local_path: str, path_s3: str, file_name: str, file_type: str) -> None:
    """
    Save a file to an S3 bucket.

    :param local_path: Path to the local file.
    :param path_s3: Path within the S3 bucket.
    :param s3_folder_name: Type of the file (xml, zip, csv, parquet)
    :param file_type: Type of the file (xml, zip, csv, parquet).
    """

    session = boto3.Session(profile_name="default")
    s3_client = session.client('s3')
    bucket_name = 'tr-risk-data-prd'
    s3_object_name = f"{path_s3}/{file_name}"

    print(f"\t\t Initialising Upload to s3://{bucket_name}/{s3_object_name}")

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

        elif file_type == 'parquet':
            content_type = 'application/octet-stream'
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
        print(f"\t\t File uploaded to s3://{bucket_name}/{s3_object_name}")

    except Exception as e:
        print(f"Error uploading file to S3: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python upload_to_s3.py <local_path> <path_s3> <file_name> <file_type>")
        sys.exit(1)
    else:
        print("Uploading %s to %s"%(sys.argv[1],sys.argv[2]))

    local_path = sys.argv[1]
    path_s3 = sys.argv[2]
    file_name = sys.argv[3]
    file_type = sys.argv[4]

    save_in_s3(local_path, path_s3, file_name, file_type)
