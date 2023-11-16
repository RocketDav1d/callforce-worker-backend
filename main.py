# system imports
from fastapi import FastAPI, Request
from fastapi import FastAPI, HTTPException, status, Body
from pydantic import BaseModel
from typing import List, Dict

# project imports
from handler.transcribe_handler import transcribe_audio_from_s3
from handler.summarize_handler import summarize
from handler.prompt_handler import prompt_with_query, embed
from handler.hubspot_handler import return_properties, save_properties_to_chroma, query_the_collection
import nltk
nltk.download('punkt')



app = FastAPI()



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


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/extract")
async def extract(payload: Dict[str, str] = Body(...)):
    print("Hit extract route: ", payload)
    # or "hubspot_access_token" not in payload or "hubspot_refresh_token" not in payload
    if "s3_key" not in payload or "userId" not in payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must include 's3_key', 'hubspot_access_token', and 'hubspot_refresh_token'",
        )
    
    # collection belongs to one UserId
    # metadata:chatId belongs to one Document
    
    file_key = payload["s3_key"]
    userId = payload["userId"]
    # hubspot_access_token = payload["hubspot_access_token"]
    # hubspot_refresh_token = payload["hubspot_refresh_token"]

    #get summary
    transcript = await transcribe_audio_from_s3(file_key)
    summary = summarize(transcript)
    print("🟢"*30)
    print(summary)
    


    #init/retrieve collection in chromadb and embed Text with metadata:chatId
    collection = await embed(transcript=transcript, file_key=file_key, collection_name=userId)

    response = {
        "s3_key": file_key,
        # "hubspot_access_token": hubspot_access_token,
        # "hubspot_refresh_token": hubspot_refresh_token,
        "summary": summary,
        "collection": collection,
        "transcript": transcript
    }
    # print(response)
    return response



@app.post("/prompt")
async def prompt(payload: Dict[str, str] = Body(...)):
    print("Hit prompt route: ", payload)
    file_key = payload["file_key"]
    collection_name = payload["userId"]
    query_input = payload["prompt"]
    language: str = "de"

    response = await prompt_with_query(file_key, collection_name, query_input, language)

    return {
        "response": response
    }



@app.post("/properties")
async def get_properties(access_token: TokenModel):
    print("Hit properties route: ", access_token.access_token)
    properties = await return_properties(access_token.access_token)
    print(properties)
    if properties is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not retrieve properties",
        )
    return properties




@app.post("/hubspot/properties/query")
async def get_properties(request: Request):
    raw_json = await request.json()
    print("Hit /hubspot/properties/query route:", raw_json)
    file_key = raw_json["s3_key"]
    userId = raw_json["userId"]
    # Assuming 'raw_json' contains a 'properties' field
    properties = [Property(**item) for item in raw_json.get('properties', [])]

    print(properties)

     # Call the function to save properties to Chroma
    try:
        query_results = await query_the_collection(file_key=file_key, userId=userId, properties=properties)
        print("QUERY RESULTS: ", query_results)
    except Exception as e:
        print(f"Error querying Chroma: {e}")
        raise HTTPException(status_code=500, detail="Error querying Chroma")

    return {"query_results": query_results}

    


@app.post("/hubspot/properties/create")
async def get_properties(properties: Dict[str, str] = Body(...)):
    print("Hit /hubspot/properties/create route:", properties)
