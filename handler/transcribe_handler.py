import os
import dotenv
from typing import Dict
import sys
from deepgram import Deepgram
import asyncio
import json
import boto3
import mimetypes


dotenv.load_dotenv()

DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY")
S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID")
S3_ACCESS_KEY_SECRET = os.environ.get("S3_ACCESS_KEY_SECRET")





async def transcribe_audio_from_s3(file_key):
    print("transcribe_audio_from_s3")
    # Initialize the Deepgram SDK
    deepgram = Deepgram(DEEPGRAM_API_KEY)
    # Initialize the AWS S3 client
    s3 = boto3.client('s3', aws_access_key_id=S3_ACCESS_KEY_ID, aws_secret_access_key=S3_ACCESS_KEY_SECRET)
    print(s3)

    try:
        # Retrieve the audio file from S3 into memory
        response = s3.get_object(Bucket="callforce-app", Key=file_key)
        audio_data = response['Body'].read()

        mime_type, _ = mimetypes.guess_type(file_key)

        # Set the source for Deepgram
        source = {
            'buffer': audio_data,
            'mimetype': mime_type
        }

        language = 'de'

        # Send the audio to Deepgram and get the response
        response = await asyncio.create_task(
            deepgram.transcription.prerecorded(
            source,
            {
                'smart_format': True,
                'punctuate': True,
                'diarize': True,
                'model': 'general',
                'version': 'beta',
                'language': 'de',
                'tier': 'enhanced'
            }
            )
        )

        # # Extract and return the transcript
        # desired_text = response["results"]["channels"][0]["alternatives"][0]["transcript"]
        desired_text = response["results"]["channels"][0]["alternatives"][0]["paragraphs"]["transcript"]
        return desired_text
    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()
        line_number = exception_traceback.tb_lineno
        print(f'line {line_number}: {exception_type} - {e}')





# async def call():
#     # Example usage:
#     bucket_name = 'callforce-app'
#     object_key = "uploads/videoplayback.mp3"
#     transcript = await transcribe_audio_from_s3(bucket_name, object_key, MIMETYPE)
#     print("Transcript:")
#     print(transcript)



# if __name__ == '__main__':
#     asyncio.run(call())
