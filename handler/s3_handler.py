import boto3
import os
import sys
from dotenv import load_dotenv
load_dotenv()

S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID")
S3_ACCESS_KEY_SECRET = os.getenv("S3_ACCESS_KEY_SECRET")

s3 = boto3.client(
    's3',
    aws_access_key_id=S3_ACCESS_KEY_ID,
    aws_secret_access_key=S3_ACCESS_KEY_SECRET

)

response = s3.download_file('callforce-app', 'uploads/1698251131144PITCH-TEAM.pdf', '1698251131144PITCH-TEAM.pdf')


