import requests, os
from dotenv import load_dotenv

load_dotenv()  
groq_api_key = os.getenv("GROQ_API_KEY")

resp = requests.get(
    "https://api.groq.com/openai/v1/models",
    headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"}
)
for m in resp.json()["data"]:
    print(m["id"])