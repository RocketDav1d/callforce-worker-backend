

class ExtractionController:
    def __init__(self, transcript_manager, embedding_manager, db_manager, response_formatter):
        self.transcript_manager = transcript_manager
        self.embedding_manager = embedding_manager
        self.db_manager = db_manager
        self.response_formatter = response_formatter

    async def extract(self, payload):
        # Extract and process transcript
        transcript = await self.transcript_manager.transcribe_audio_from_s3(payload["s3_key"])
        summary = self.transcript_manager.summarize_transcript(transcript)

        # Embed and save to database
        chunks = self.transcript_manager.chunk_transcript_with_speaker(transcript)
        embeddings = await self.embedding_manager.get_embeddings_concurrently(chunks)
        embeddings_name = await self.db_manager.save_to_vectordb(embeddings=embeddings, chunked_transcript=chunks,collection_name=payload["userId"] ,file_key=payload["s3_key"])


        # Format and return the response
        return self.response_formatter.format_extract_response(file_key=payload["s3_key"], summary=summary, collection_name=embeddings_name, transcript=transcript)