

class PromptController:
    def __init__(self, database_manager, embedding_manager, prompt_manager):
        self.database_manager = database_manager
        self.embedding_manager = embedding_manager
        self.prompt_manager = prompt_manager


    async def prompt(self, file_key, collection_name, query_input, language):
        # Extract and process transcript
        query_embedding = await self.embedding_manager.get_embedding(query_input)
        query_results = await self.database_manager.query_collection(file_key, collection_name, query_embedding)
        result = await self.prompt_manager.prompt(query_results, query_input, language) 

        # rerturn the response
        return result