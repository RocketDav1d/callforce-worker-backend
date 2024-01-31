import os
import openai
from dotenv import load_dotenv

class PromptManager:
    def __init__(self):
        load_dotenv()
        # self.api_key = os.environ.get("OPENAI_API_KEY")
        openai.api_key = os.environ.get("OPENAI_API_KEY")
        print("openai.api_key", openai.api_key)

    async def prompt(query_results, query_input, language):
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
        try: 
            response = openai.ChatCompletion.create(
                model=MODEL,
                messages=messages  # Adjust the max_tokens as needed for your response length
            )
            response_data = response['choices'][0]['message']['content']
            # print("response_data", response_data)
            # response_dict = eval(response_data)  # Convert the string to a dictionary

            # answer = response_dict['answer']
            # context_text = response_dict['context_text']
            print("response_data", response_data)
            return response_data
        
        except openai.error.InvalidRequestError as e:
            print(f"Skipping embedding for invalid text: {messages}")
            print(f"Error: {str(e)}")
            return None
