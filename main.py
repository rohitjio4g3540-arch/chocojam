import os 
import requests 
from fastapi import FastAPI 
from dotenv import load_dotenv 
 
load_dotenv() 
 
app = FastAPI() 
 
API_KEY = os.getenv("v1.CmQKHHN0YXRpY2tleS1lMDBndGY0NWdjYjF6MG1ieHcSIXNlcnZpY2VhY2NvdW50LWUwMGd3a3Byd3d0cjB3MHQwMjIMCIWF-9UGELns8IEBOgwIhIiToQcQgPbpvAFAAloDZTAw.AAAAAAAAAAF1AfL-ESS6IayJQJQktOifawvTk-HeBS15MbrrdMwndKEJXxZkxsc_znkWcBCq2MAObVqMV-76Duai16WmOToA") 
 
MODEL_URL = "https://api.tokenfactory.nebius.com/v1/chat/completions"


@app.get("/")
def root():
    return {"message": "ChocoJam is running"}


@app.post("/ask-model")
def ask_model(input_text: str):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "zai-org/GLM-5.3",
        "messages": [
            {
                "role": "user",
                "content": input_text,
            }
        ],
    }

    response = requests.post(
        MODEL_URL,
        headers=headers,
        json=data,
    )

    return response.json()