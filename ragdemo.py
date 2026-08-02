from elasticsearch import Elasticsearch
from openai import OpenAI

# -------------------------
# CONNECT
# -------------------------

es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", ""),
    verify_certs=False
)

client = OpenAI()

# -------------------------
# RETRIEVAL
# -------------------------

def retrieve_passages(query_text, k=5):
    response = es.search(
        index="msmarco",
        body={
            "size": k,
            "query": {
                "match": {
                    "text": query_text
                }
            }
        }
    )

    passages = []

    for i, hit in enumerate(response["hits"]["hits"], start=1):
        source = hit.get("_source", {})
        passages.append({
            "rank": i,
            "doc_id": source.get("doc_id"),
            "text": source.get("text", "")
        })

    return passages


# -------------------------
# GENERATION
# -------------------------

def generate_answer(query_text, passages):
    context = ""

    for p in passages:
        context += f"[Passage {p['rank']} | Doc ID: {p['doc_id']}]\n"
        context += p["text"][:1200] + "\n\n"

    prompt = f"""
You are a RAG assistant. Answer the question using ONLY the retrieved passages below.

If the passages do not contain enough information, say:
"The retrieved passages do not provide enough information to answer confidently."

Question:
{query_text}

Retrieved passages:
{context}

Answer:
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt
    )

    return response.output_text


# -------------------------
# DEMO
# -------------------------

query = "what is machine learning"

passages = retrieve_passages(query, k=5)

print("\nTOP RETRIEVED PASSAGES")
print("=" * 60)

for p in passages:
    print(f"\nRank {p['rank']}")
    print("Doc ID:", p["doc_id"])
    print("Text:", p["text"][:300])

print("\n\nGENERATED RAG ANSWER")
print("=" * 60)

answer = generate_answer(query, passages)
print(answer)
