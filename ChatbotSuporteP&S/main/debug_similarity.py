"""
Script para debugar por que a busca semântica não encontra chunks relevantes com alta similaridade
"""
from src.rag.vectorstore import get_vectorstore

# Teste 1: Query original
query1 = "Quem é o autor do manual?"
vectorstore = get_vectorstore()
results1 = vectorstore.similarity_search_with_score(query1, k=7)

print("=" * 80)
print(f"QUERY 1: '{query1}'")
print("=" * 80)
for i, (doc, score) in enumerate(results1, 1):
    content = doc.page_content[:100].replace("\n", " ")
    print(f"{i}. Score: {score:.2%}")
    print(f"   Conteudo: {content}...")
    if "autor" in doc.page_content.lower() or "gabriel" in doc.page_content.lower():
        print("   [CONTAINS AUTHOR INFO]")
    print()

# Teste 2: Query mais específica
query2 = "Gabriel Henrique de Lima"
results2 = vectorstore.similarity_search_with_score(query2, k=7)

print("=" * 80)
print(f"QUERY 2: '{query2}'")
print("=" * 80)
for i, (doc, score) in enumerate(results2, 1):
    content = doc.page_content[:100].replace("\n", " ")
    print(f"{i}. Score: {score:.2%}")
    print(f"   Conteudo: {content}...")
    print()

# Teste 3: Query apenas "autor"
query3 = "autor"
results3 = vectorstore.similarity_search_with_score(query3, k=7)

print("=" * 80)
print(f"QUERY 3: '{query3}'")
print("=" * 80)
for i, (doc, score) in enumerate(results3, 1):
    content = doc.page_content[:100].replace("\n", " ")
    print(f"{i}. Score: {score:.2%}")
    print(f"   Conteudo: {content}...")
    print()

# Teste 4: Mostra o chunk que contém "Autor(a): Gabriel"
print("=" * 80)
print("CHUNK COM AUTHOR (indice 0):")
print("=" * 80)
print(vectorstore._data[0]["page_content"][:500])
