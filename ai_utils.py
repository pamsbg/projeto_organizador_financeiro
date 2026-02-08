import google.generativeai as genai
import json
import time

def classify_transactions_gemini(descriptions, categories, api_key):
    """
    Classifica uma lista de descrições usando o Google Gemini.
    Retorna um dicionário {descrição: categoria}.
    """
    if not api_key:
        return {}
    
    genai.configure(api_key=api_key)
    
    
    # Modelo Flash é rápido e barato (ou free tier)
    # Tentando versão Lite para evitar Rate Limit e 404
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-lite-001')
    except:
        model = genai.GenerativeModel('gemini-flash-latest')
    
    
    # Prompt Otimizado com Contexto
    prompt = f"""
    Você é um assistente financeiro pessoal inteligente. 
    Seu objetivo é classificar transações financeiras com base no nome do estabelecimento ou descrição.
    
    Categorias Oficiais: {', '.join(categories)}
    
    Regras de Ouro:
    1. "Nowpark", "Estapar", "Sem Parar", "Park", "Estacionamento" devem ir para Transporte (Combustível/Estacionamento/Manutenção).
    2. Uber, 99, Táxi vão para Transporte (Uber/99).
    3. Ifood, Restaurantes, Bares vão para Lazer/Restaurantes.
    4. Farmácias vão para Saúde/Farmácia.
    5. Supermercados, Sacolão vão para Alimentação (Mercado/Sacolão).
    
    Se não souber ou for ambíguo, use "Outros".
    Responda APENAS com um objeto JSON válido (sem markdown, sem ```json) onde a chave é a descrição exata e o valor é a categoria escolhida.
    
    Transações para classificar:
    {json.dumps(descriptions, ensure_ascii=False)}
    """
    
    # Tentativa com Retry Simples para evitar 429 (Rate Limit)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            # Limpar markdown do JSON se houver (```json ... ```)
            text_response = response.text.strip()
            if text_response.startswith("```json"):
                text_response = text_response[7:-3].strip()
            elif text_response.startswith("```"):
                text_response = text_response[3:-3].strip()
                
            result = json.loads(text_response)
            return result
        except Exception as e:
            if "429" in str(e):
                # Rate Limit - Esperar exponencialmente
                wait_time = (2 ** attempt) + 1
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    continue
            print(f"Erro na IA: {e}")
            return {}
            
    return {}
