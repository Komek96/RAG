from elasticsearch import Elasticsearch

# 1️⃣ CONNECT
es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", ""),
    verify_certs=False
)

# 2️⃣ ADD DEBUG STEPS HERE 👇
print("Initial count:", es.count(index="msmarco"))

es.indices.refresh(index="msmarco")
print("Index refreshed.")

print("Count after refresh:", es.count(index="msmarco"))

# 3️⃣ TEST SEARCH (very important)
response = es.search(
    index="msmarco",
    body={
        "size": 3,
        "query": {
            "match": {
                "text": "github"
            }
        }
    }
)

print("Test search hits:", response["hits"]["total"])
print("Sample hit:", response["hits"]["hits"][:1])

print("Count:", es.count(index="msmarco"))

print("Count:", es.count(index="msmarco"))

response = es.search(
    index="msmarco",
    body={
        "size": 3,
        "query": {
            "match": {
                "text": "github"
            }
        }
    }
)

print(response["hits"]["total"])
print(response["hits"]["hits"][:1])
