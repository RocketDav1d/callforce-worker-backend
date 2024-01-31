import asyncio
import hashlib
import time
import chromadb

class DatabaseManager:
    def __init__(self, host, port):
        self.chroma_client = chromadb.HttpClient(host=host, port=port)

    def generate_id(self, text_chunk, index):
        content_hash = hashlib.md5(text_chunk.encode()).hexdigest()
        unique_id = f"{content_hash}_{index}_{int(time.time())}"
        return unique_id

    async def save_to_vectordb(self, embeddings, chunked_transcript, collection_name, file_key):
        print("Saving to ChromaDB...")

        # Generate ids for each chunk
        ids = [self.generate_id(chunk, idx) for idx, chunk in enumerate(chunked_transcript)]

        # Create collection
        collection = self.chroma_client.get_or_create_collection(name=collection_name)

        # Prepare the data for ChromaDB insert
        documents = chunked_transcript
        metadatas = [{"transcript_chunk": chunk, "document": file_key} for chunk in chunked_transcript]

        # Run the synchronous ChromaDB insert in the default executor
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: collection.add(documents=documents, embeddings=embeddings, metadatas=metadatas, ids=ids))
        
        print(f"Saved {len(chunked_transcript)} embeddings to ChromaDB in collection '{collection_name}'")
        return collection_name

    async def query_the_collection(self, file_key, collection_name, query_embedding):
        collection = self.chroma_client.get_or_create_collection(name=collection_name)
    
        print("Inside query_the_collection with collection", collection, "and query_embedding", query_embedding)

        query = collection.query(
            query_embeddings=query_embedding,
            # query_texts=[query_input],
            n_results=6,
            where={"document": file_key},
            )
        print("query", query)
        return query
