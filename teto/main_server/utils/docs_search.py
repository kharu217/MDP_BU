import os
import numpy as np
import pandas as pd
import ollama

from tqdm import tqdm


CSV_PATH = r"C:\Users\kharu217\Documents\teto\book_crawl\book_data\total.csv"
EMBEDDING_PATH = r"C:\Users\kharu217\Documents\teto\main_server\utils\book_embeddings.npy"

EMBED_MODEL = "qwen3-embedding:4b"

df = pd.read_csv(CSV_PATH)

BATCH_SIZE = 32

def get_embeddings_batch(texts: list[str]) -> np.ndarray:
    response = ollama.embed(
        model=EMBED_MODEL,
        input=texts,
        dimensions=512
    )
    return np.array(response["embeddings"], dtype=np.float16)


def build_embedding_cache():
    texts = [
        f"book title : {row['book_name']} \n book description : {row['book_desc']} \n book author : {row['author']}"
        for _, row in df.iterrows()
    ]

    embeddings = []

    for i in tqdm(range(0, len(texts), BATCH_SIZE), desc="Embedding books"):
        batch = texts[i:i + BATCH_SIZE]
        emb = get_embeddings_batch(batch)
        embeddings.append(emb)

    embeddings = np.vstack(embeddings)

    np.save(EMBEDDING_PATH, embeddings)
    print(f"\nSaved embeddings: {embeddings.shape}")


def load_embeddings():
    embd = np.load(EMBEDDING_PATH)
    print(embd.shape)
    return np.load(EMBEDDING_PATH)


def search_books(
    query: str,
    top_k: int = 5
):

    embeddings = load_embeddings()

    query_embedding = get_embeddings_batch(query)[0]

    # 코사인 유사도 계산
    scores = (
        embeddings @ query_embedding
    ) / (
        np.linalg.norm(
            embeddings,
            axis=1
        )
        * np.linalg.norm(query_embedding)
    )

    top_indices = np.argsort(
        scores
    )[::-1][:top_k]

    results = []

    for idx in top_indices:
        results.append({
            "book_name": df.iloc[idx]["book_name"],
            "author": df.iloc[idx]["author"],
            "publisher": df.iloc[idx]["publisher"],
            "published_y": df.iloc[idx]["published_y"],
            "book_desc": df.iloc[idx]["book_desc"],
            "book_img_link": df.iloc[idx]["book_img_link"],
            "is_enable": bool(df.iloc[idx]["is_enable"])
        })

    return results

def search_books_for_prompt(query: str,
    top_k: int = 5
):

    embeddings = load_embeddings()

    query_embedding = get_embeddings_batch([query])[0]

    # 코사인 유사도 계산
    scores = (
        embeddings @ query_embedding
    ) / (
        np.linalg.norm(
            embeddings,
            axis=1
        )
        * np.linalg.norm(query_embedding)
    )

    top_indices = np.argsort(
        scores
    )[::-1][:top_k]

    results = []

    for idx in top_indices:
        results.append({
            "book_name": df.iloc[idx]["book_name"],
            "book_desc": df.iloc[idx]["book_desc"]
        })
    print(results)

    return results

def print_results(results):
    print("\n검색 결과\n")

    for rank, item in enumerate(
        results,
        start=1
    ):
        print("=" * 80)
        print(f"인덱스      : {rank}")
        print(f"제목      : {item['book_name']}")
        print(f"저자      : {item['author']}")
        print(f"출판사    : {item['publisher']}")
        print(f"출간년도  : {item['published_y']}")
        print(f"이미지    : {item['book_img_link']}")
        print()
        print("줄거리")
        print(item["book_desc"])
        print()


if __name__ == "__main__":
    print(search_books_for_prompt("프란츠 카프카의 소설 중 벌레를 다룬 소설"))
