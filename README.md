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


## Environment Variables

For this worker to work you need to signup at:
- [OpenAI](https://openai.com/)
- [AWS S3](https://aws.amazon.com/de/s3/)
- [Deepgram](https://deepgram.com/)



