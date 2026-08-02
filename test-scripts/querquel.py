from elasticsearch import Elasticsearch

es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", ""),
    verify_certs=False
)

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

def search_ids(es, query_text, k=10):
    response = es.search(
    index="msmarco",
    body={
        "size": k,
        "query": {
            "match": {
                "text": {
                    "query": query_text
                }
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

def precision_at_10(retrieved_ids, relevant_ids):
    hits = sum(1 for doc_id in retrieved_ids[:10] if doc_id in relevant_ids)
    return hits / 10.0

queries = load_queries("queries.train.tsv")
qrels = load_qrels("qrels.train.tsv")

print("Loaded queries:", len(queries))
print("Loaded qrels:", len(qrels))

test_qids = list(qrels.keys())[:5]
scores = []

for qid in test_qids:
    query_text = queries.get(qid)
    if query_text is None:
        print(f"Skipping qid {qid}: not found in queries file")
        continue

    retrieved = search_ids(es, query_text, k=10)
    relevant = qrels.get(qid, set())
    p10 = precision_at_10(retrieved, relevant)
    scores.append(p10)

    print("\n" + "=" * 60)
    print("Query ID:", qid)
    print("Query:", query_text)
    print("Top 10 doc_ids:", retrieved)
    print("Relevant doc_ids count:", len(relevant))
    print("P@10:", round(p10, 3))

if scores:
    avg_p10 = sum(scores) / len(scores)
    print("\nAverage P@10:", round(avg_p10, 3))
else:
    print("\nNo queries were successfully evaluated.")

with open("results.txt", "w") as f:
    ...
