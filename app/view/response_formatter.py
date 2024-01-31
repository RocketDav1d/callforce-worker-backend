class ResponseFormatter:
    def format_extract_response(self, file_key, summary, collection_name, transcript):
        # Format the response
        # return {
        #     "summary": summary,
        #     "db_response": db_response
        # }
    
        response = {
            "s3_key": file_key,
            # "hubspot_access_token": hubspot_access_token,
            # "hubspot_refresh_token": hubspot_refresh_token,
            "summary": summary,
            "collection": collection_name,
            "transcript": transcript
        }
        return response
