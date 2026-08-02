from elasticsearch import Elasticsearch

es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", ""),
    verify_certs=False
)

def search(query_text, k=10):
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

    for i, hit in enumerate(response["hits"]["hits"], start=1):
        source = hit.get("_source", {})
        print(f"Rank {i}")
        print("Score:", hit.get("_score"))
        print("Doc ID:", source.get("doc_id", "N/A"))
        print("Text:", source.get("text", "")[:200])
        print()
print(search_ids(es, "github", k=5))
