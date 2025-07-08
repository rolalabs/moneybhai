import outlines
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

GEN_AI_CLIENT = genai.Client(api_key=os.getenv('GENAI_API_KEY'))

MODEL = outlines.from_gemini(GEN_AI_CLIENT, "gemini-2.5-flash")