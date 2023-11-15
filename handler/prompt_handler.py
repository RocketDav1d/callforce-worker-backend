import asyncio
import aiohttp
import re
import os
import openai
import hashlib
import time
import dotenv
import chromadb
from typing import Dict
import time
import sys
from deepgram import Deepgram
import asyncio, json

dotenv.load_dotenv()

# Intialize ChromaDb
# chroma_client = HttpClient(host="localhost", port = 8000, settings=Settings(allow_reset=True, anonymized_telemetry=False))
chroma_client = chromadb.Client()

# Initialize OpenAI
openai.api_key = "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"




# 📨 Init ChromaDB with collection and add embeddings ---------------------------------------------

def generate_id(text_chunk, index):
    content_hash = hashlib.md5(text_chunk.encode()).hexdigest()
    unique_id = f"{content_hash}_{index}_{int(time.time())}"
    return unique_id


# 1. Chunk the Transcript:
def chunk_transcript_with_speaker(transcript_text):
    # Extracting all segments for each speaker
    segments = re.findall(r"(Speaker \d+: .*?)(?=\n\nSpeaker \d+:|$)", transcript_text, re.DOTALL)
    # Chunking based on the principles mentioned
    chunks = []
    for segment in segments:
        speaker_info, content = segment.split(':', 1)
        # Splitting the segment by sentences
        sentences = re.split(r'(?<=[.!?])\s+', content.strip())
        # Initialize a new chunk
        chunk = []
        for sentence in sentences:
            chunk.append(sentence.strip())
            # Consider a maximum of 7 sentences per chunk for simplicity (can be adjusted)
            if len(chunk) >= 2:
                chunks.append(f"{speaker_info}: {' '.join(chunk)}")
                chunk = []
        # Adding remaining sentences to chunks
        if chunk:
            chunks.append(f"{speaker_info}: {' '.join(chunk)}")
    return chunks


# 2. Embed the Chunks
async def get_embedding(text_to_embed):
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


async def get_embeddings_concurrently(chunked_transcript):
    print("Getting embeddings concurrently...")
    # Creating a list of coroutine objects
    embedding_tasks = [get_embedding(text) for text in chunked_transcript]
    # Running the coroutines concurrently and collecting the results
    embeddings = await asyncio.gather(*embedding_tasks)
    print(f"Generated {len(embeddings)} embeddings")
    return embeddings


# 3. save to Vector Database
async def save_to_vectordb(vectordb_client, embeddings, chunked_transcript, collection_name, file_key):
    print("Saving to Chroma...")

    # Generate ids for each chunk
    ids = [generate_id(chunk, idx) for idx, chunk in enumerate(chunked_transcript)]

    # Create collection
    collection = vectordb_client.get_or_create_collection(name=collection_name)

    # Prepare the data for Chroma insert
    documents = chunked_transcript
    metadatas = [{"transcript_chunk": chunk, "document": file_key} for chunk in chunked_transcript]

    # Run the synchronous Chroma insert in the default executor
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: collection.add(documents=documents, embeddings=embeddings, metadatas=metadatas, ids=ids))
    
    print(f"Saved {len(chunked_transcript)} embeddings to Chroma in collection '{collection_name}'")

    return collection_name


# Execute chain
async def save_embeddings(transcript, file_key, collection_name):
    print("save embeddings")
    # Chunk the transcript
    chunked_transcript = chunk_transcript_with_speaker(transcript)
    # print("Chunked Transcript: ", chunked_transcript)
    # Get the embeddings for the transcript chunks
    # start = time.time()
    embeddings = await get_embeddings_concurrently(chunked_transcript)
    # end = time.time()
    # print("Embeddings: ", embeddings, "\nTime taken: ", end-start)
    # Save the embeddings to ChromaDb
    collection_name = await save_to_vectordb(vectordb_client=chroma_client, embeddings=embeddings, chunked_transcript=chunked_transcript, collection_name=collection_name, file_key=file_key)
    return collection_name





# 🔍 Query the Collection ---------------------------------------------

async def query_the_collection(file_key, collection_name, query_input):
    collection = chroma_client.get_or_create_collection(name=collection_name)
    embedding = await get_embedding(query_input)

    print("collection", collection)
    print("embedding", embedding)

    query = collection.query(
        query_embeddings=embedding,
        # query_texts=[query_input],
        n_results=6,
        where={"document": file_key},
        )
    print("query", query)
    return query


def generate_response_with_context_and_id(query_results, api_key, query_input, language):
    # Extract the documents and query input from query_results
    documents = query_results.get("documents", [])
    print("documents", documents) 
    context_text = documents[0]
    # print("documents", context_text)

    messages = [
        {"role": "system", "content": f"You are a helpful assistant who answers to all questions give the provided context from the Context Dictionary. Your answer is in {language}"},
        {"role": "user", "content": "Use this Context Array to the answer the question: \n"},
        {"role": "user", "content": "Context Text Items: \n".join([f"Item {i+1}: {item}" for i, item in enumerate(context_text)])},
        {"role": "user", "content": 'return in this format {"answer": "concise short answer from a third person perspective", "context_text": "the ONLY ONE of the 6 context_text_items which was used as context"}'},
        {"role": "user", "content": "Query: " + query_input },
    ]

    MODEL = "gpt-3.5-turbo"
    # Call OpenAI API to get the response
    response = openai.ChatCompletion.create(
        model=MODEL,
        messages=messages  # Adjust the max_tokens as needed for your response length
    )

    response_data = response['choices'][0]['message']['content']
    # print("response_data", response_data)
    # response_dict = eval(response_data)  # Convert the string to a dictionary

    # answer = response_dict['answer']
    # context_text = response_dict['context_text']

    return response_data






# 🟢 Executive functions ---------------------------------------------

async def embed(transcript, file_key, collection_name):
    collection_name = await save_embeddings(transcript, file_key, collection_name)
    return collection_name


async def prompt_with_query(file_key, collection_name, query_input, language):
    query_results = await query_the_collection(file_key, collection_name, query_input)
    # response, context_text = generate_response_with_context_and_id(query_results, openai.api_key, query_input, language)
    response = generate_response_with_context_and_id(query_results, openai.api_key, query_input, language)
    print("Response:", response)
    return response













































# old code


# def prompt(chat_id, collection_name, query_input):
#     query_results = asyncio.run(query_the_collection(chat_id, collection_name, query_input))
#     response, context_text = generate_response_with_context_and_id(query_results, openai.api_key, query_input)
#     return response, context_text


# def extraxt_response():
#     while True:
#         collection_name = input(f"Collection Name:")
#         if collection_name == "exit":
#             print('Exiting')
#             sys.exit()
#         chat_id = input(f"Chat ID:")
#         if chat_id == "exit":
#             print('Exiting')
#             sys.exit()
#         query_input = input(f"Query:")
#         if query_input == "exit":
#             print('Exiting')
#             sys.exit()

#         # Run the save_embeddings function
#         asyncio.run(save_embeddings(chat_id, collection_name))

#         # Run the query_the_collection function and print the results
#         query_results = asyncio.run(query_the_collection(chat_id, collection_name, query_input))

#         # Generate the response with context and document ID
#         response, context_text = generate_response_with_context_and_id(query_results, openai.api_key, query_input)
#         print(f"Response: {response}")
#         print(f"Document ID: {context_text}")







# def map_ids_to_integers(query_results):
#     # Extract the IDs and documents from query_results
#     ids = query_results.get("ids", [])
#     documents = query_results.get("documents", [])

#     # Create dictionaries to map IDs to integers and vice versa
#     id_to_integer_mapping = {}
#     integer_to_id_mapping = {}

#     # Iterate through the IDs and documents and assign integers
#     for i, (id_list, document_list) in enumerate(zip(ids, documents)):
#         # Take the first ID as the key and the corresponding document as the value
#         id_key = id_list[0]
#         document_value = document_list[0]

#         # Assign an integer (starting from 1) to the ID
#         integer_key = str(i + 1)
#         id_to_integer_mapping[id_key] = integer_key
#         integer_to_id_mapping[integer_key] = id_key

#     return id_to_integer_mapping, integer_to_id_mapping



# def create_id_to_document_mapping(query_results):
#     ids = query_results.get("ids", [])
#     documents = query_results.get("documents", [])

#     id_to_document_mapping = {}

#     for id_list, document_list in zip(ids, documents):
#         for id, document in zip(id_list, document_list):
#             id_to_document_mapping[id] = document

#     return id_to_document_mapping







transcript = "\nSpeaker 0: Just I can kind of frame frame the discussion of the, you know, are you guys mostly cold calling from, like, a dialer from, your phones? Are you, are you on zoom, a decent amount?\n\nSpeaker 1: Yeah. We're on a zoom, a decent amount because, the, intricole on always happens on Zoom. It's not an easy to understand product, I would say. So, like, our customers are most I have a lot of questions and have, like, very specific, ideas of what they have in mind and want to clarify if we can offer that. So, that's yeah.\n\nI've never seen someone use the phone, mostly, like, only 4. If you already know person maybe gives you a phone call. But, like, the for outreach to to customers, we don't have a connection to always be a Zoom or Google Meet.\n\nSpeaker 0: Got it. Got it. And then, I guess, how many folks on your team are doing those calls on on Zoom?\n\nSpeaker 1: We have about 5 salespeople.\n\nSpeaker 0: Okay. Yeah. Okay. Cool. Cool.\n\nAnd then what's the do you guys do the in the back, or I guess\n\nSpeaker 1: what you guys can keep me as HubSpot.\n\nSpeaker 0: Oh, great. Yeah. Yeah. We support HubSpot. So and what are some of the things that you guys typically are are trying to, like, what kind of information are you guys trying to gather on the call?\n\nLike, how many calls do you guys typically have with each of these customers?\n\nSpeaker 1: I would say about 2 or 3 So, like, the first call is really like an introductory call. It's mostly about 10 minutes, and it's, usually them an idea. And then afterwards, they come up with the, like, real questions, so to speak, when they're yeah. And, really dig deeper into, like, their use cases, what they want us to support.\n\nSpeaker 0: Yeah.\n\nSpeaker 1: So, yeah, they often have, like, as I said, very specific questions, in edge cases, they want to to clarify. If we support them.\n\nSpeaker 0: Okay. Okay. And I guess, are your calls typically in in German or in English? Or\n\nSpeaker 1: 70 or something that was there about in German. Yeah. We're expanding to the UK, though, so increasing the English as well.\n\nSpeaker 0: Okay. So German, German, and English.\n\nSpeaker 1: Yeah. Pretty much. And done. Alright.\n\nSpeaker 0: Cool. Yeah. We we we do support both German, and and and English. Okay. That's as well.\n\nI can I can confirm, but I'm pretty sure we support? Just give me one second. It's probably your support. You said, Dutch. Right?\n\nIs that is that what you're looking for?\n\nSpeaker 1: Exactly. Yeah.\n\nSpeaker 0: Yes. We support Dutch.\n\nSpeaker 1: Oh, okay.\n\nSpeaker 0: Yeah. Super. It's more join German English and Dutch. Okay. Cool.\n\nSo as so it sounds like your your salespeople make these calls And currently, they are logging a bunch of information from those calls, right, into HubSpot. Is that right?\n\nSpeaker 1: Yeah. We have a pipeline in place. And the entry point is usually those calls.\n\nSpeaker 0: Gotcha. And are you are you just, like, looking for a tool to assist the sales team, or are you, like, having issues, having the sales team actually putting that information in. Is there more information we'd like to have in that, you know, than the sales people have capacity to put in? Like, what is, I guess, yeah, give me some some of the shape of that.\n\nSpeaker 1: Yeah, exactly because it's so crucial. Like, as I said, lots of customers have very specific ideas of what they want. We really need to keep track of that of, like, what they actually want. And sometimes in longer calls, it can be a hassle to keep track of that afterwards, like, trying to remember, okay, what what were the, like, the key points they need from our product? So that's, I would say, very crucial.\n\nAnd so I was, this is and I've seen that you, have this feature with your product. Right? So that this part, my interest, I have to say. And, yeah, that's what I wanted to see how the product works.\n\nSpeaker 0: Okay. Cool. Yeah. Yeah. That makes sense.\n\nOkay. And then what's the what's sort of the structure of your sales team? Is it, like, 5, like, just 5 sales reps? Is there, like, a head of sales? Do you guys have, like, SDRs, or, like, is it kind of just, like, 5 folks who all do sales and report to, like, the CEO or or something.\n\nSpeaker 1: It's, yeah, mostly mostly the last, currently, I have to say we're still not a very big company. And, also, the salespeople have sort of different boxes, as I said, like some for the K, some for Germany, some for the Netherlands.\n\nSpeaker 0: And and how big how big is your company?\n\nSpeaker 1: We're pushing 35 people.\n\nSpeaker 0: Okay. Cool. Cool. Yeah. I can give you I can give you, like, a a quick look at what our what our products, especially, especially around the use case that you're describing, what it looks like.\n\nAnd then, you know, we can discuss if if something that you think would be interested to you guys, and then we can we can discuss, like, you know, we can potentially, like, have you guys do, like, like, take a look at it from there?\n\nSpeaker 1: Mhmm. Sounds good.\n\nSpeaker 0: Alright. So what you're gonna see here is, what gets generated, when when I when I pull this up here in a second, what you're going to see is the card that we generate from every every call with all of the information, everything on the card is editable, and most of the or most of everything on the card is syncable to the CRO. And I'll show how how kind of Tell you show me what that looks like.\n\nSpeaker 1: Mhmm.\n\nSpeaker 0: So I'm just showing my screen here. Okay. Can you start screen?\n\nSpeaker 1: Oh, yeah.\n\nSpeaker 0: Alright. So this is a sample call, from the call. You'll see the first thing we generate a summary. So the idea here is that I am this this is this is syncable to the CRM. The idea here is that for every call that occurs, this quickly allows either leadership or other folks who will need to be involved in the deal or the rep themselves.\n\nTo quickly see sort of what happened, like, catch back up on, like, what happened during each of the calls. And we can actually provide a decent amount of detail in in this So this this will get all get synced as notes or, like, a logged activity in HubSpot on the record. Outside is actually one of the first CRMs we ever worked with. And you'll see, essentially, the the summary there, we can actually include quite a bit of detail in the summary too, including numbers or specific requests or things like that. If we move it move to the right hand side here, this entire section is actually all of the notes that gets synced into HubSpot as as the activity specifically.\n\nThere's other pieces that get synced elsewhere, but as an activity, you'll see that we have the summary, and we also have All of the questions the rep asked, as well as answers that the prospects gave and vice versa. And everything here is rewritten for sort of completeness and clarity so that it's easy to, you know, see exactly what happened during the conversation. And, again, you can actually click here to jump into the conversation to see what happened during that as well. So if there's specific questions, you know, that your reps are asking, you can go in and see what the what the customer answered to find that information. And that's just one of the ways to find the information.\n\nI'll show you another way in a second as well. And additionally, we plot some high as well. So just some, like, key points from the conversation. And all of this gets flattened and synced in as an activity, which then again, also links back out to this card so you can look at the details. On the left hand side, you'll see that we also pull out the next steps for every call.\n\nSo this lets you see what needs to happen on the, like, you know, what folks commit to on the call. As far as, you know, next steps or follow-up items on the syncs to the, to the next steps field in HubSpot as well. And then the heavy lifting we have here as well is we have these custom fields. So custom fields, these can actually be anything. So these map directly to fields inside of HubSpot, or or can map directly into fields inside of HubSpot.\n\nThey can be numbers, pick lists, short answers, multi selects, anything, anything like that. And what we can do is, you can configure this so that it can pull out any information UI and sync it directly to HubSpot. Let's say there are, like, certain things, cert certain requests that, like you said, that, like, the customer has. Right? So, like, if they're, if you want, like, a list of all the items that are, like, nonnegotiable for the customer, or something or, like, some features they want.\n\nYou can put that into a custom field, to keep it here or sync it sync it to this to this to the CR\n\nSpeaker 1: But the, a quick question. The other, apart from the custom fields, summary, for example, is also synced to HubSpot or\n\nSpeaker 0: Yes. Yes. So this this whole car, this whole side gets picked into HubSpot as a logged activity.\n\nSpeaker 1: Ah, okay. So then Like\n\nSpeaker 0: a logged call, like a logged call.\n\nSpeaker 1: Okay. Yeah.\n\nSpeaker 0: So it shows up in the ex activity feed inside HubSpot. So you can kinda click, like, you can you can see these notes inside a website.\n\nSpeaker 1: Mhmm. Okay.\n\nSpeaker 0: Or alternatively, you can click from that and jump back into our our platform as well. And there's some cool stuff for if you're in our platform, you know, you get you get, you know, obviously, like, basic review functionality, like, creating snippets, writing comments, we have some coaching functionality or 2, like, scorecards. And for for you guys, actually, we can we can turn on product insights as well. This is like a SaaS specific feature. Right?\n\nSo we didn't pull out, like, what features did they talk about, for example. So these are literally, like, what features did the customer mention? What did they say about it? And so forth, since you guys seems like also sell software.\n\nSpeaker 1: Oh, yeah.\n\nSpeaker 0: Yeah. And then, And then this this and then, yeah, it was in a transcript here. You can obviously click around. You can see who's talking and when. Something our customers have found very useful, though, is that if you're looking for specific information, We actually create this outline, with summaries.\n\nSo you can actually click through and jump into any part of the conversation that you'd like to relisten to that part of the conversation to see what happened there. Mhmm. So, you know, if your policy, like, the conversation about pricing, Lynn, you can go into any call and and just click in click into this, this outline that we\n\nSpeaker 1: have. Yeah.\n\nSpeaker 0: Yeah. That's the that's the that's the basics of it. Beyond this, we have some functionality that we have a library where you can create playlists, search through calls, things like that. And you saw always some coaching munching odds here on scorecards and, and so forth. But this is the, this is the, I have a main piece that's relevant to you.\n\nSpeaker 1: Yeah. I've looked at a bunch of tools. So, I I'm not sure I remember correctly, but, with pilot, there isn't, like, call it research feature where I can pull up research about a prospect in advance before I have the call so that I, like, already know what I'm getting myself into and, like, how I can structure the call.\n\nSpeaker 0: Sure. Sure. So we do have, we do have the, a feature for that. But it's still quite early. Our feature mostly pulls up historical information that is inside of pilot and also pulls up, information from within the CRM.\n\nSpeaker 1: Mhmm.\n\nSpeaker 0: That makes sense. So you can see your past calls. We have what you talked about with them and then information that's inside the system. But you're talking about additionally, like, information from, like, the open web, right, as well. Right?\n\nLike, information about the company, like, people information from LinkedIn, things like that. Is that right?\n\nSpeaker 1: Yeah.\n\nSpeaker 0: Yeah. That's a doc that piece is something that we're we're working on. Is that is that something that you think you feel is kinda critical to the workflow for your sales rep?\n\nSpeaker 1: It's definitely very helpful, yeah, too, because we often end up having to do some, or do some research in advance to understand, like, how we should structure the call and, like, what products What's\n\nSpeaker 0: right.\n\nSpeaker 1: For example, we should, like, send them in advance Yeah.\n\nSpeaker 0: What sort of information would you be looking for, in the the research?\n\nSpeaker 1: Mainly, like this, for example, what this. If it's an, journal partner, fund manager, we're talking to it. Look at what kind of funds he has been, leading in the past. So try to understand, like, how the, like, how experienced the, fund managers or, for example, we have product for founders where we can help them onboard their angel investors. So this would also be something interesting to us, like, how experienced the founders and, like, what the companies.\n\nHe is, yeah, founding what it's about and, like, this sort of stuff.\n\nSpeaker 0: Got it. So it's, like, mostly stuff based play around the person's experience, and then also, potentially information around the, the company itself, company or So yeah. Right. So it's probably information that's mostly from LinkedIn. Is that accurate?\n\nSpeaker 1: Yeah. Most of the time, it's just from LinkedIn. Yeah.\n\nSpeaker 0: You do most of your your research on LinkedIn. Right? Yeah. That's something we we we certainly will will at some point incorporate. Hopefully, hopefully, hopefully, soon.\n\nSpeaker 1: Okay. But like there isn't a specific, there there's no specific feature already in, production, I would say.\n\nSpeaker 0: So we do so the the feature I mentioned that we have in production is mostly centered around information that's our you already have inside of your CRM and also information here, but we are, we are actively working on the future you're describing of pulling information in from, from LinkedIn. What are what are some of the other solutions that you you've looked at to just so I so I so I understand and and and kind of what have you found particularly either useful or, or what have been kind of your thoughts on them so far?\n\nSpeaker 1: You mean other tools? Or\n\nSpeaker 0: Yeah. Other tools. Yeah.\n\nSpeaker 1: To be honest, for the, like, summarization feature, yeah, like, your guys I would say the only one, but for example, there's crystal crystal knows for pulling up information about a person Wait. Let me search this. Where is it?\n\nSpeaker 0: Crystalknows.com. No. You're a buyer before he's on.\n\nSpeaker 1: Yeah.\n\nSpeaker 0: Interesting. Okay. And this is, yeah, this is more for, like, kind of getting, like, information about them.\n\nSpeaker 1: Yeah. Exactly. And there was\n\nSpeaker 0: Resent.\n\nSpeaker 1: Yeah, a fan investor, I think.\n\nSpeaker 0: What's that?\n\nSpeaker 1: What's it? Fanned Ambassador.\n\nSpeaker 0: Fanned Ambassador? Like, like, ghostbusters.\n\nSpeaker 1: Yeah.\n\nSpeaker 0: Yeah. I see that. Yeah. Very cool. Okay.\n\nYeah. Yeah. Well, no. That is something that we are working on. I need to definitely, like, you know, it's something we are aware of and something we are we have other customers who have requested as well.\n\nSpeaker 1: Okay.\n\nSpeaker 0: As far as, yeah, as far as kinda call call call proper Christian.\n\nSpeaker 1: Yeah. Just sort of interest, like, how how big are you guys? Is it, I've seen you at YC, right? Is it, already quite a big big company with product teams in place, or is it, okay,\n\nSpeaker 0: yeah. We're, no, we're small. We're definitely smaller than than you guys are are now. We we're we're, eight people. But, yeah, we, I mean, we have, a sizable customer base and, our our product's been in the market for about a year.\n\nSo as well as the signature.\n\nSpeaker 1: Okay. Alright. Yeah. So you've got got some traction. That's what I'm that's what I mean.\n\nSpeaker 0: Yeah. Yeah. Yeah. Yeah. Correct.\n\nThat's good. You can see some of our customers on our our website as awesome of our our are sizable. Some of them are, we have customers smaller than you guys. We have customers larger than you guys. Mhmm.\n\nSo, yeah, it runs prevents the range.\n\nSpeaker 1: Cool. Yeah, nice. I I like the product. I hope I have no It's pretty straightforward. It's somewhat what I expected, I have to say.\n\nSo I have, like, immediate further question. Yeah.\n\nSpeaker 0: So\n\nSpeaker 1: I'm I'm gonna but I'm also gonna be honest with you, the the decision is not with me. Like, I'm not the one who makes the\n\nSpeaker 0: calls. Sure. Sure. I guess what information, what information do you feel like, your I guess first who who who's making who's making the the decision on this on this one?\n\nSpeaker 1: The automation lead. So The automation lead? Yeah.\n\nSpeaker 0: Okay. And on on the automation lead, how do you how do you think, I can do to help help them make that decision? I guess, what's her name?\n\nSpeaker 1: Jacob.\n\nSpeaker 0: Jacob. Okay. So so so, I guess, would you would you think do you think it'd be helpful for Jacob to see the see the platform. Like, could you should we schedule a follow-up meeting with Jacob, you know, in some time?\n\nSpeaker 1: Or Yeah. I think what I'm gonna do is talk to Jacob about tool, and then we'll see together if, like, because, like, internally we have a lot of operate, like, automations in place, our company is sort of, yeah, built from the ground up on automating every operational process. So, yeah, we're gonna see, like, as we u we often do this to determine if a tool is actually worth it off, we can automate it ourselves in some way. And to be honest, in a lot of ways, we can automate it ourselves, but we still, personally, as a love to look into other tools, and then we see it makes sense to integrate them in our tool stack, or, yeah, as I said, to try to do it ourselves.\n\nSpeaker 0: Well, I mean, definitely use this. Oh, yeah. Go ahead.\n\nSpeaker 1: No. Awesome. I'm gonna just run through with Jacob, about the discussion we just had, and then we're gonna make a decision. Yeah.\n\nSpeaker 0: Yeah. Yeah. Yeah. Well, definitely use me as resource if you have any other further questions or anything like that. If you'd like, we can set a, meeting, maybe a week from now.\n\nAnd if you guys decide to move on, you know, move move on to do it yourselves, we can cancel the meeting. If if you decide that, you know, Jacob wants to wants to see it as well, we can, we can invite Jacob to the call. Do you wanna just set up a time? Like, do you wanna just meet at the same time maybe in a week?\n\nSpeaker 1: Yeah. Sure. Yeah.\n\nSpeaker 0: Okay. I'm just gonna duplicate this meeting then for 1 week from now. That'll be, August 7th. Monday at the same time.\n\nSpeaker 1: It's not\n\nSpeaker 0: too late for you. Right? I know it's a little bit better.\n\nSpeaker 1: It's okay. Yeah. It's\n\nSpeaker 0: fine. Okay. Okay.\n\nSpeaker 1: Alright.\n\nSpeaker 0: Great.\n\nSpeaker 1: Thanks for your time, Maxwell.\n\nSpeaker 0: Awesome. Thank\n\nSpeaker 1: you. Then see you. And Have\n\nSpeaker 0: a great day.\n\nSpeaker 1: Bye bye."