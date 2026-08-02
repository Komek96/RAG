from elasticsearch import Elasticsearch
from openai import OpenAI
import re

# =========================
# CONNECT TO ELASTICSEARCH
# =========================
es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", ""),
    verify_certs=False
)

client = OpenAI()
# =========================
# HELPER FUNCTIONS
# =========================

def load_queries(path):
    queries = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t", 1)
            if len(parts) != 2:
                continue
            qid, text = parts
            queries[qid] = text
    return queries


def load_qrels(path):
    qrels = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 4:
                continue
            qid, _, doc_id, rel = parts
            if int(rel) > 0:
                qrels.setdefault(qid, set()).add(doc_id)
    return qrels


def clean_query(q):
    q = q.lower().strip()
    q = re.sub(r"^[^\w]+", "", q)  # remove weird leading symbols
    return q


def search_ids(es, query_text, k=10):
    query_text = clean_query(query_text)

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

    results = []
    for hit in response["hits"]["hits"]:
        source = hit.get("_source", {})
        doc_id = source.get("doc_id")
        if doc_id is not None:
            results.append(str(doc_id))

    return results


def search_full(es, query_text, k=3):
    query_text = clean_query(query_text)

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

    return response["hits"]["hits"]


def precision_at_10(retrieved_ids, relevant_ids):
    hits = sum(1 for doc_id in retrieved_ids[:10] if doc_id in relevant_ids)
    return hits / 10.0


# =========================
# MAIN EXECUTION
# =========================

print("Checking index...")
print("Document count:", es.count(index="msmarco"))

# Load files (update filenames if needed)
queries = load_queries("queries.train.tsv")
qrels = load_qrels("qrels.train.tsv")

print("Loaded queries:", len(queries))
print("Loaded qrels:", len(qrels))

# Find overlapping query IDs
common_qids = list(set(queries.keys()) & set(qrels.keys()))

# Limit to 5 queries for assignment
test_qids = common_qids[:5]

scores = []

# =========================
# EVALUATION LOOP
# =========================

with open("results.txt", "w", encoding="utf-8") as f:

    for qid in test_qids:
        query_text = queries[qid]

        retrieved = search_ids(es, query_text, k=10)
        relevant = qrels[qid]

        p10 = precision_at_10(retrieved, relevant)
        scores.append(p10)

        # PRINT
        print("\n" + "=" * 60)
        print("Query ID:", qid)
        print("Query:", query_text)
        print("Top 10 doc_ids:", retrieved)
        print("Relevant doc_ids count:", len(relevant))
        print("P@10:", round(p10, 3))

        # SAVE
        f.write(f"Query ID: {qid}\n")
        f.write(f"Query: {query_text}\n")
        f.write(f"Top 10 doc_ids: {retrieved}\n")
        f.write(f"Relevant doc_ids count: {len(relevant)}\n")
        f.write(f"P@10: {round(p10, 3)}\n")
        f.write("=" * 60 + "\n")

    # Average
    if scores:
        avg_p10 = sum(scores) / len(scores)
        print("\nAverage P@10:", round(avg_p10, 3))

        f.write(f"\nAverage P@10: {round(avg_p10, 3)}\n")
    else:
        print("\nNo queries evaluated.")

# =========================
# CUSTOM QUERIES
# =========================

print("\n\nRunning custom queries...\n")

custom_queries = [
    "what is agentic RAG",
    "who invented the telephone",
    "what is machine learning",
    "how does photosynthesis work",
    "what causes earthquakes"
]

with open("results.txt", "a", encoding="utf-8") as f:

    f.write("\n\n===== CUSTOM QUERIES =====\n")

    for query in custom_queries:
        print("\n" + "-" * 60)
        print("Custom Query:", query)

        f.write("\n" + "-" * 60 + "\n")
        f.write(f"Custom Query: {query}\n")

        results = search_full(es, query, k=10)

        for i, hit in enumerate(results, start=1):
            source = hit.get("_source", {})

            doc_id = source.get("doc_id")
            text = source.get("text", "")[:300]

            # PRINT
            print(f"\nRank {i}")
            print("Doc ID:", doc_id)
            print("Text:", text)

            # SAVE
            f.write(f"\nRank {i}\n")
            f.write(f"Doc ID: {doc_id}\n")
            f.write(f"Text: {text}\n")
# =========================
# RAG ANSWER GENERATION
# =========================

def generate_rag_answer(query_text, passages):
    context = ""

    for p in passages:
        source = p.get("_source", {})
        context += f"[Doc ID: {source.get('doc_id')}]\n"
        context += source.get("text", "")[:1200] + "\n\n"

    prompt = f"""
You are a retrieval-augmented generation assistant.

Answer the question using ONLY the retrieved passages below.
If the passages do not contain enough information, say:
"The retrieved passages do not provide enough information to answer confidently."

Question:
{query_text}

Retrieved Passages:
{context}

Answer:
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt
    )

    return response.output_text

print("\n\nRunning RAG demo...\n")

rag_queries = [
    "what is machine learning",
    "how does photosynthesis work",
    "what causes earthquakes"
]

with open("results.txt", "a", encoding="utf-8") as f:
    f.write("\n\n===== RAG GENERATED ANSWERS =====\n")

    for query in rag_queries:
        print("\n" + "=" * 60)
        print("RAG Query:", query)

        passages = search_full(es, query, k=5)
        answer = generate_rag_answer(query, passages)

        print("\nGenerated Answer:")
        print(answer)

        f.write("\n" + "=" * 60 + "\n")
        f.write(f"RAG Query: {query}\n\n")
        f.write("Generated Answer:\n")
        f.write(answer + "\n")
