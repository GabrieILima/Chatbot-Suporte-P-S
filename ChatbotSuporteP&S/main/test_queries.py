"""
Teste final: Validando qualidade de busca com novos parâmetros
"""
import os
import requests
from langchain_openai import ChatOpenAI
from src.rag.vectorstore import get_vectorstore

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")

llm = ChatOpenAI(api_key=OPENAI_API_KEY, model=MODEL_NAME)

def ollama_answer(query, context, model="llama3"):
    url = "http://localhost:11434/api/generate"
    prompt = f"Responda de forma objetiva e curta à pergunta abaixo, usando apenas o contexto fornecido. Se não souber, responda 'Não encontrado'.\n\nPergunta: {query}\n\nContexto:\n{context}"
    payload = {"model": model, "prompt": prompt, "stream": False}
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json().get("response", "[Sem resposta]")
    except Exception as e:
        return None

def hf_answer(query, context, model="mistralai/Mistral-7B-Instruct-v0.2", token=None):
    url = f"https://api-inference.huggingface.co/models/{model}"
    prompt = f"Responda de forma objetiva e curta à pergunta abaixo, usando apenas o contexto fornecido. Se não souber, responda 'Não encontrado'.\n\nPergunta: {query}\n\nContexto:\n{context}"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    payload = {"inputs": prompt}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("generated_text", "[Sem resposta]")
        elif isinstance(result, dict) and "generated_text" in result:
            return result["generated_text"]
        return "[Sem resposta]"
    except Exception as e:
        return None

def rag_answer(query, k=3):
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search_with_score(query, k=k)
    context = "\n\n".join([doc.page_content for doc, score in results])
    # Tenta Ollama
    resposta = ollama_answer(query, context)
    if resposta:
        return resposta
    # Fallback HuggingFace
    hf_token = os.getenv("HF_TOKEN")
    resposta = hf_answer(query, context, token=hf_token)
    if resposta:
        return resposta
    return "[Nenhuma resposta gerada]"

# Exemplo de uso:
if __name__ == "__main__":
    query = "Quem é o solicitante?"
    print("Pergunta:", query)
    try:
        vectorstore = get_vectorstore()
        results = vectorstore.similarity_search_with_score(query, k=3)
        context = "\n\n".join([doc.page_content for doc, score in results])
        print("\n[DEBUG] Contexto enviado ao LLM:\n", context[:500], "...\n")
        resposta = rag_answer(query, k=3)
        print("\nResposta curta:", resposta)
    except Exception as e:
        print("[ERRO] Falha ao consultar LLM:", repr(e))

vectorstore = get_vectorstore()

queries = [
    "Quem eh o autor?",
    "Gabriel Henrique",
    "Qual o nome da pessoa que fez este documento?",
    "Documentacao TAC",
    "Painel de Acompanhamento"
]

for query in queries:
    results = vectorstore.similarity_search_with_score(query, k=3)
    print(f"\nQuery: '{query}'")
    print("-" * 70)
    for i, (doc, score) in enumerate(results, 1):
        content = doc.page_content[:80].replace("\n", " ")
        print(f"{i}. {score:.1%}: {content}...")
