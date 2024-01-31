import re
import os
import sys
import boto3
import asyncio
import mimetypes
from deepgram import Deepgram
from dotenv import load_dotenv
from handler.summarize_handler import Summarizer


class TranscriptManager:
    def __init__(self):
        # Load environment variables
        load_dotenv()

        # Retrieve credentials from environment variables
        self.deepgram_api_key = os.environ.get("DEEPGRAM_API_KEY")
        self.s3_access_key_id = os.environ.get("S3_ACCESS_KEY_ID")
        self.s3_access_key_secret = os.environ.get("S3_ACCESS_KEY_SECRET")

        # Initialize the Deepgram SDK
        self.deepgram = Deepgram(self.deepgram_api_key)

        # Initialize the AWS S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.s3_access_key_id,
            aws_secret_access_key=self.s3_access_key_secret
        )

    async def transcribe_audio_from_s3(self, file_key, bucket_name='callforce-app', language='de'):
        try:
            # Retrieve the audio file from S3 into memory
            response = self.s3_client.get_object(Bucket=bucket_name, Key=file_key)
            print("s3 response: ", response)    
            audio_data = response['Body'].read()

            mime_type, _ = mimetypes.guess_type(file_key)

            # Set the source for Deepgram
            source = {
                'buffer': audio_data,
                'mimetype': mime_type
            }

            # Transcription settings
            transcription_settings = {
                'smart_format': True,
                'punctuate': True,
                'diarize': True,
                'model': 'general',
                'version': 'beta',
                'language': language,
                'tier': 'enhanced'
            }
            # Send the audio to Deepgram and get the response
            response = await asyncio.create_task(
                self.deepgram.transcription.prerecorded(source, transcription_settings)
            )
            
            #Extract and return the transcript
            # desired_text = response["results"]["channels"][0]["alternatives"][0]["transcript"]
            desired_text = response["results"]["channels"][0]["alternatives"][0]["paragraphs"]["transcript"]
            if not desired_text:
                desired_text = "No transcript found"
                print("No transcript found")
            print("transciption successful")
            return desired_text
        except Exception as e:
            exception_type, exception_object, exception_traceback = sys.exc_info()
            line_number = exception_traceback.tb_lineno
            print(f'line {line_number}: {exception_type} - {e}')

    def chunk_transcript_with_speaker(self, transcript_text):
        print("chunk_transcript_with_speaker, Transcript Text", transcript_text)
        # Extracting all segments for each speaker
        segments = re.findall(r"(Speaker \d+: .*?)(?=\n\nSpeaker \d+:|$)", transcript_text, re.DOTALL)
        chunks = []
        for segment in segments:
            speaker_info, content = segment.split(':', 1)
            sentences = re.split(r'(?<=[.!?])\s+', content.strip())
            chunk = []
            for sentence in sentences:
                chunk.append(sentence.strip())
                if len(chunk) >= 2:  # Adjust as necessary
                    chunks.append(f"{speaker_info}: {' '.join(chunk)}")
                    chunk = []
            if chunk:
                chunks.append(f"{speaker_info}: {' '.join(chunk)}")
        return chunks
    
    def summarize_transcript(self, transcript_text, language='german'):
        # Initialize Summarizer
        summ = Summarizer(language=language)
        summary = summ.summarize(transcript_text)
        return summary

    # def summarize_transcript(self, transcript_text):
    #     # Summarize the transcript. This method could be as simple or complex as needed
    #     # For example, it could just truncate the transcript, or perform a more complex summary.
    #     # Here, we'll just demonstrate a simple truncation for brevity
    #     summary_length = 100  # characters
    #     return transcript_text[:summary_length] + '...' if len(transcript_text) > summary_length else transcript_text

    # Additional methods related to transcript processing can be added here
