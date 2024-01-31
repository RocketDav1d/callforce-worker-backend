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
from hubspot import HubSpot
import time
import sys
from deepgram import Deepgram
import asyncio, json
from translate import Translator
from dotenv import load_dotenv
from pprint import pprint

class HubspotManager:
    def __init__(self):
        pass


    async def _fetch_properties(self, session, object_type, access_token):
        url = f'https://api.hubapi.com/crm/v3/properties/{object_type}'
        headers = {'Authorization': "Bearer " + access_token}

        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._extract_properties(data, object_type)
                else:
                    return {object_type: f"Failed to fetch properties, status code: {response.status}"}
        except Exception as e:
            print(f"Exception when calling HubSpot API: {str(e)}")
            return {object_type: "Failed to fetch properties"}

    def _extract_properties(self, data, object_type):
        results = data.get('results', [])
        properties = [{'name': prop.get('name', ''),
                       'description': prop.get('description', ''),
                       'label': prop.get('label'),
                       'hidden': prop.get('hidden'),
                       'archived': prop.get('archived'),
                       'object_type': object_type} for prop in results]
        return {object_type: properties}

    async def fetch_all_properties(self, access_token):
        async with aiohttp.ClientSession() as session:
            types = ["contacts", "companies", "deals"]
            tasks = [self._fetch_properties(session, object_type, access_token) for object_type in types]
            properties = await asyncio.gather(*tasks)
            return dict((k, v) for d in properties for k, v in d.items())
        

    async def create_object(self, object_type, access_token):
        url = f'https://api.hubapi.com/crm/v3/objects/{object_type}/'
        headers = {'Authorization': "Bearer " + access_token}
        payload = {
            "properties": {
                "amount": "1500.00",
                "dealname": "Custom data integrations",
                "pipeline": "default",
                "closedate": "2019-12-07T16:50:06.678Z",
                "dealstage": "presentationscheduled",
                "hubspot_owner_id": "1208641524"
            } 
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        return {f"Failed to create {object_type}, status code: {response.status}"}
            except Exception as e:
                print(f"Exception when calling HubSpot API: {str(e)}")
                return {object_type: "Failed to create properties"}


        

    # async def _fetch_properties(session, object_type, access_token):
    #     url = f'https://api.hubapi.com/crm/v3/properties/{object_type}'
    #     headers = {
    #         'authorization': "Bearer " + access_token,
    #     }
        
    #     try:
    #         async with session.get(url, headers=headers) as response:
    #             if response.status == 200:
    #                 data = await response.json()
    #                 # print(data)
    #                 # return data
    #                 results = data.get('results', [])
    #                 properties = []
    #                 for prop in results:
    #                     name = prop.get('name', '')
    #                     print(name)
    #                     description = prop.get('description', '')
    #                     # embedding_name = await get_embedding(name)
    #                     # embedding_description = await get_embedding(description)
    #                     property_dict = {
    #                         "name": name,
    #                         "description": description,
    #                         # "embedding_name": embedding_name,
    #                         # "embedding_description": embedding_description,
    #                         "label": prop.get('label'),
    #                         "hidden": prop.get('hidden'),
    #                         "archived": prop.get('archived'),
    #                         "object_type": object_type
    #                     }
    #                     properties.append(property_dict)
    #                 # print(properties)
    #                 return {object_type: properties}
    #             else:
    #                 return {object_type: f"Failed to fetch properties, status code: {response.status}"}
    #     except Exception as e:
    #         print(f"Exception when calling HubSpot API: {str(e)}")
    #         return {object_type: "Failed to fetch properties"}
        
    # async def return_properties(access_token):
    #     async with aiohttp.ClientSession() as session:
    #         types = ["contacts", "companies", "deals"]
    #         tasks = [fetch_properties(session, object_type, access_token) for object_type in types]
    #         properties = await asyncio.gather(*tasks)
    #         print("PROPERTIES: ", properties)
    #         return properties