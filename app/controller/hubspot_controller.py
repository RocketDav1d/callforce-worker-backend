

class HubspotController:
    def __init__(self, hubspot_manager):
        self.hubspot_manager = hubspot_manager


    async def getProperties(self, access_token):
        # Extract and process transcript
        properties = await self.hubspot_manager.fetch_all_properties(access_token) 
        return properties
    

    async def createObject(self, object_type, access_token):
        created_object = await self.hubspot_manager.create_object(object_type, access_token)
        return created_object