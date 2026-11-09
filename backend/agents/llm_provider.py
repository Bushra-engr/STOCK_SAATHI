import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path, override=True)
load_dotenv(override=True)

groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError("GROQ_API_KEY is missing in your .env file!")

llm = ChatGroq(
    model_name="qwen/qwen3.8-27b",
    groq_api_key=groq_api_key,
    temperature=0.2,
)
