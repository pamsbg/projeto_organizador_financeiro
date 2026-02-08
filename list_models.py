import google.generativeai as genai
import toml
import os

try:
    secrets = toml.load(".streamlit/secrets.toml")
    api_key = secrets["gemini_api_key"]
    genai.configure(api_key=api_key)
    
    print("Listando modelos disponíveis:")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
            
except Exception as e:
    print(f"Erro: {e}")
