from elasticsearch import Elasticsearch, helpers
from tqdm import tqdm

es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", ""),
    verify_certs=False
)

START_LINE = 6427670   # number already indexed
FILE_PATH = "fulldocs.tsv"

prepared = 0
skipped = 0

def generate_docs():
    global prepared, skipped

    with open(FILE_PATH, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(tqdm(f, desc="Indexing"), start=1):
            if line_num <= START_LINE:
                continue

            line = line.rstrip("\n")
            parts = line.split("\t", 1)

            if len(parts) != 2:
                skipped += 1
                continue

            doc_id, text = parts

            if not doc_id or not text:
                skipped += 1
                continue

            prepared += 1

            yield {
                "_index": "msmarco",
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

print("Prepared docs:", prepared)
print("Skipped malformed:", skipped)
print("Indexed successfully:", success)
print("Errors:", len(errors))

es.indices.refresh(index="msmarco")
print("Final count:", es.count(index="msmarco"))
