from elasticsearch import Elasticsearch
from openai import OpenAI
import streamlit as st
import re

# -------------------------
# Elasticsearch connection
# -------------------------
es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", ""),
    verify_certs=False
)

client = OpenAI()

INDEX_NAME = "msmarco"


# =========================
# HELPERS
# =========================

def clean_query(q):
    q = q.lower().strip()
    q = re.sub(r"^[^\w]+", "", q)
    return q

def simplify_query(q):
    stopwords = {
        "what", "is", "are", "was", "were", "the", "a", "an",
        "of", "to", "in", "on", "for", "and", "or", "how", "does"
    }
    words = re.findall(r"\w+", q.lower())
    keywords = [w for w in words if w not in stopwords]
    return " ".join(keywords)

def length_bucket(text):
    words = text.split()
    n = len(words)

    if n < 50:
        return "Short"
    elif n < 150:
        return "Medium"
    else:
        return "Long"


def search_passages(query_text, k=50):
    query_text = clean_query(query_text)

    response = es.search(
        index=INDEX_NAME,
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
        text = source.get("text", "")

        results.append({
            "rank": len(results) + 1,
            "score": hit.get("_score", 0),
            "doc_id": source.get("doc_id"),
            "text": text,
            "length_bucket": length_bucket(text),
            "word_count": len(text.split())
        })

    return results


def generate_rag_answer(query_text, passages):
    context = ""

    for p in passages:
        context += f"[Rank {p['rank']} | Doc ID: {p['doc_id']}]\n"
        context += p["text"][:1200] + "\n\n"

    prompt = f"""
You are a retrieval-augmented generation assistant.

Use the retrieved passages to answer the question as directly and confidently as possible.

Rules:
1. Base your answer primarily on the retrieved passages.
2. If the passages give partial information, answer using the strongest supported information.
3. Do not say you cannot answer unless the passages are completely unrelated.
4. Keep the answer clear and concise.
5. Mention when the answer is based on retrieved evidence.

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


# =========================
# SIMPLE SEARCH INTERFACE
# =========================

st.set_page_config(page_title="MS MARCO RAG Search", layout="wide")

st.title("MS MARCO RAG Search Interface")
st.write("Local Elasticsearch BM25 retrieval with faceted filtering and optional RAG answer generation.")

query = st.text_input("Enter a search query:")

top_k = st.slider(
    "Number of results to retrieve before filtering",
    min_value=10,
    max_value=100,
    value=50,
    step=10
)

st.sidebar.header("Faceted Filtering")

selected_lengths = st.sidebar.multiselect(
    "Passage length facet",
    ["Short", "Medium", "Long"],
    default=["Short", "Medium", "Long"]
)

min_score = st.sidebar.slider(
    "Minimum Elasticsearch score",
    min_value=0.0,
    max_value=50.0,
    value=0.0,
    step=0.5
)

show_word_count = st.sidebar.checkbox("Show word count", value=True)

use_rag = st.sidebar.checkbox("Generate RAG answer from filtered results", value=False)

rag_context_count = st.sidebar.slider(
    "Number of passages for RAG answer",
    min_value=1,
    max_value=10,
    value=10
)

if st.button("Search"):
    if not query.strip():
        st.warning("Please enter a query.")
    else:
        results = search_passages(query, k=top_k)
        if not results:
            simple_query = simplify_query(query)
            results = search_passages(simple_query, k=top_k)

        filtered_results = [
            r for r in results
            if r["length_bucket"] in selected_lengths and r["score"] >= min_score
        ]

        st.subheader("Facet Summary")

        short_count = sum(1 for r in results if r["length_bucket"] == "Short")
        medium_count = sum(1 for r in results if r["length_bucket"] == "Medium")
        long_count = sum(1 for r in results if r["length_bucket"] == "Long")

        st.write(f"Short passages: {short_count}")
        st.write(f"Medium passages: {medium_count}")
        st.write(f"Long passages: {long_count}")

        st.subheader(f"Filtered Search Results: {len(filtered_results)} shown")

        if use_rag and filtered_results:
            st.subheader("Generated RAG Answer")

            rag_passages = filtered_results[:rag_context_count]
            answer = generate_rag_answer(query, rag_passages)

            st.write(answer)

        for r in filtered_results[:10]:
            with st.expander(
                f"Rank {r['rank']} | Score: {r['score']:.2f} | {r['length_bucket']}"
            ):
                st.write(f"**Doc ID:** {r['doc_id']}")

                if show_word_count:
                    st.write(f"**Word Count:** {r['word_count']}")

                st.write(r["text"])
