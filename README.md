# Callforce.ai - FastApi Worker Backend

## Function

This backend enables the NextJS app to:
- transcribe audio
- summarise transcript
- chunck & embed transcript


## Get started

Afer cloning this project run in your venv activated
```bash
pip install -r requirements.txt
```

After that run this commnd to run the app locall on port 8000
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

For development you can initialise a Chroma instace with ```chromadb.Client()```

If you want to deploy your project you'll need to deploy Chroma
This is easiest with AWS
A good tutorial on how to so can be found in the [Chroma Docs](https://docs.trychroma.com/deployment) or in this [Video](https://www.youtube.com/watch?v=xRIEKjOosaM)



## Environment Variables

For this worker to work you need to signup at:
- [OpenAI](https://openai.com/)
- [AWS S3](https://aws.amazon.com/de/s3/)
- [Deepgram](https://deepgram.com/)



