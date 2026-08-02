from elasticsearch import Elasticsearch, helpers
from tqdm import tqdm

es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", ""),
    verify_certs=False
)

FILE_PATH = "collection.tsv"

def generate_docs():
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        for line in tqdm(f, desc="Indexing"):
            line = line.rstrip("\n")
            parts = line.split("\t", 1)

            if len(parts) != 2:
                continue

            doc_id, text = parts
            if not doc_id or not text:
                continue

            yield {
                "_index": "msmarco",
                "_id": doc_id,
                "_source": {
                    "doc_id": doc_id,
                    "text": text
                }
            }

success, errors = helpers.bulk(
    es,
    generate_docs(),
    chunk_size=500,
    raise_on_error=False
)

es.indices.refresh(index="msmarco")
print("Indexed successfully:", success)
print("Errors:", len(errors))
print("Final count:", es.count(index="msmarco"))
