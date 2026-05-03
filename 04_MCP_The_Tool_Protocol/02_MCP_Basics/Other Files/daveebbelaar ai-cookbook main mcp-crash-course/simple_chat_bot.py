
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise SystemExit("Missing GOOGLE_API_KEY in environment or .env file.")

client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents="Say hello in one short sentence.",
)
print(response.text)
