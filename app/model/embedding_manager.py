import asyncio
import openai
import os
import re
from dotenv import load_dotenv

class EmbeddingManager:
    def __init__(self):
        load_dotenv()
        # self.api_key = os.environ.get("OPENAI_API_KEY")
        openai.api_key = os.environ.get("OPENAI_API_KEY")


    async def get_embedding(self, text_to_embed):
        # print(f"Embedding text: {text_to_embed}")
        try:
            response = await openai.Embedding.acreate(
                model="text-embedding-ada-002",
                input=text_to_embed
            )
            embedding = response["data"][0]["embedding"]
            return embedding
        except openai.error.InvalidRequestError as e:
            print(f"Skipping embedding for invalid text: {text_to_embed}")
            print(f"Error: {str(e)}")
            return None
        
    
    async def get_embeddings_concurrently(self, chunked_transcript):
        print("Getting embeddings concurrently...", chunked_transcript)
        embedding_tasks = [self.get_embedding(text) for text in chunked_transcript]
        embeddings = await asyncio.gather(*embedding_tasks)
        print(f"Generated {len(embeddings)} embeddings")
        return embeddings


    


