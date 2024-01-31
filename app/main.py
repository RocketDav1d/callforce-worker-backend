# system imports
from fastapi import FastAPI, Request
from fastapi import FastAPI, HTTPException, status, Body
from pydantic import BaseModel
from typing import List, Dict
import nltk
import time
nltk.download('punkt')

# project imports
#controller
from app.controller import ExtractionController, PromptController, HubspotController

#models / manager
from app.model import (TranscriptManager, EmbeddingManager, DatabaseManager,
                       PromptManager, HubspotManager)
#formatter
from app.view import ResponseFormatter


#initialize models
class TokenModel(BaseModel):
    access_token: str

class Property(BaseModel):
    id: str
    name: str
    label: str
    description: str
    type: str
    createdAt: str
    userId: str

class CreateObjectModel(BaseModel):
    object_type: str
    access_token: str

# initialize app
app = FastAPI()



# Dependency Injection
transcript_manager = TranscriptManager()
embedding_manager = EmbeddingManager()
db_manager = DatabaseManager(host="18.197.143.82", port=8000)
response_formatter = ResponseFormatter()
prompt_manager = PromptManager()
hubspot_manager = HubspotManager() 


# initialize controllers
extraction_controller = ExtractionController(transcript_manager, embedding_manager, db_manager, response_formatter)
prompt_controller = PromptController(prompt_manager, embedding_manager, prompt_manager)
hubspot_controller = HubspotController(hubspot_manager, )




# endpoints
@app.post("/extract")
async def extract_endpoint(payload: dict = Body(...)):
    start = time.time()
    # Validate payload
    if "s3_key" not in payload or "userId" not in payload:
        raise HTTPException(status_code=400, detail="Missing required fields in payload")
    
    print("Hit extract route: ", payload)
    
    file_key = payload["s3_key"]
    userId = payload["userId"]

    # Call the extraction controller
    response = await extraction_controller.extract(payload)
    end = time.time()
    duration = end - start
    print(f"Extract took {duration} seconds")
    return response


@app.post("/prompt")
async def prompt_endpoint(payload: dict = Body(...)):
    start = time.time()
    print("Hit prompt route: ", payload)
    file_key = payload["file_key"]
    collection_name = payload["userId"]
    query_input = payload["prompt"]
    language: str = "de"

    if not file_key or not collection_name or not query_input:
        raise HTTPException(status_code=400, detail="Missing required fields in payload")
    
    response = await prompt_controller.prompt(file_key, collection_name, query_input, language)

    end = time.time()
    duration = end - start
    print(f"Prompt took {duration} seconds")

    return {
        "response": response
    }


@app.post("/properties")
async def get_properties(access_token: TokenModel):
    print("Hit properties route: ", access_token.access_token)
    properties = await hubspot_controller.getProperties(access_token.access_token)
    print(properties)
    if properties is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not retrieve properties",
        )
    return properties




@app.post("/create_object")
async def create_object(request: CreateObjectModel):
    print("Hit create_objects route: ", request.access_token)
    properties = await hubspot_controller.createObject(request.object_type, request.access_token)
    print(properties)
    if properties is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not retrieve properties",
        )
    return properties