from flask import Flask, request, jsonify, Response, stream_with_context
from flask_restful import Resource, Api, reqparse, abort
import polars as pl
import json
import os
from utils.docs_search import search_books, search_books_for_prompt
from ollama import Client
import math
import numpy as np
import cv2
import threading
import queue

book_list = pl.read_csv(r"..\book_crawl\book_data\total.csv")
client = Client(
    host="https://ollama.com",
    headers={'Authorization': 'Bearer ' + os.environ["OLLAMA_API_KEY"]}
)

with open(r"utils\README.md", "r", encoding="utf-8") as f:
    system_prompt = f.read()

app = Flask(__name__)
app.json.ensure_ascii = False  # 추가
api = Api(app)

# 이전 대화를 그냥 리스트로 들고 있는다. 프로세스가 살아있는 동안만 유지되고,
# 서버 재시작하면 비워진다. 또한 모든 클라이언트가 이 하나의 리스트를 공유하므로
# 동시에 여러 사람이 쓰면 대화가 섞인다. 1인 사용 기준 단순 구현이다.
chat_history = []
MAX_TURNS = 10  # user+assistant 한 쌍 기준 최대 보관 개수

import math

def sanitize_for_json(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    return obj

@app.route('/get_random_book')
def get_random_book():
    book_type = request.args.get('book_type')
    filtered = book_list if book_type == "" else book_list.filter(pl.col("book_type") == book_type)

    random_book = filtered.sample(3)
    while random_book["book_img_link"].has_nulls():
        random_book = filtered.sample(3)

    return jsonify(random_book.to_dicts())

@app.route('/search_book', methods=["GET"])
def search_book() :
    query = request.args.get('query')  # get_json() 아님
        
    query_norm = query.replace(" ", "").lower()

    searched_book = book_list.filter(pl.col("book_name").str.replace_all(r"\s+", "").str.to_lowercase().str.contains(query_norm, literal=True) | pl.col("author").str.replace_all(r"\s+", "").str.to_lowercase().str.contains(query_norm, literal=True)).sort(pl.col("book_name"))
    print(searched_book)
    return jsonify(searched_book.to_dicts())

@app.route('/lm_search_book')
def lm_search_book() :
    query = request.args.get('query')
    searched_book = search_books(query, top_k=5)
    return(jsonify(searched_book))

@app.route('/lm_chat')
def lm_chatting() :
    query_text = request.args.get('query')

    user_query = {
        'role': 'user',
        'content': query_text + "\n\n" + str(search_books_for_prompt(query_text, top_k=50))
    }
    system_query = {
        'role': 'system',
        'content':  system_prompt
    }
    messages = [system_query] + chat_history + [user_query]

    def generate():
        full_answer = []
        stream = client.chat(
            'gemma4:31b',
            messages=messages,
            think='low',
            stream=True
        )
        for chunk in stream:
            content = chunk['message']['content']
            if content:
                full_answer.append(content)
                yield f"data: {json.dumps({'token': content}, ensure_ascii=False)}\n\n"

        chat_history.append(user_query)
        chat_history.append({'role': 'assistant', 'content': "".join(full_answer)})

        max_messages = MAX_TURNS * 2
        if len(chat_history) > max_messages:
            del chat_history[:len(chat_history) - max_messages]

        # 답변에서 언급/근거로 쓰인 책 목록을 별도 이벤트로 전송
        recommended_books = search_books(query_text, top_k=150)
        recommended_books = sanitize_for_json(recommended_books)
        yield f"data: {json.dumps({'type': 'books', 'books': recommended_books}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"
        
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

setted_book = ""
@app.route('/set_bookdata', methods=["POST"])
def set_bookdata():
    global setted_book
    bookinfo = request.get_json()
    if bookinfo is None:
        return {"error": "invalid json"}, 400
    setted_book = bookinfo
    print(bookinfo)
    return {"received": bookinfo}, 200

@app.route('/get_bookdata', methods=["GET"])
def get_bookdata() :
    global setted_book
    return jsonify(setted_book)

@app.route('/del_bookdata', methods=["DELETE"])
def del_bookdata() :
    global setted_book
    setted_book = ''
    return ''

@app.route('/check', methods=['GET'])
def check():
    global setted_book
    exists = bool(setted_book)  # 또는 DB EXISTS 쿼리
    return '', 200 if exists else 204

frame_queue = queue.Queue(maxsize=1)
stop_event = threading.Event()

@app.route('/upload_image', methods=["POST"])
def upload_image():
    if 'image' not in request.files:
        return {"error": "no image field"}, 400

    file = request.files['image']
    if file.filename == '':
        return {"error": "empty filename"}, 400

    img_bytes = np.frombuffer(file.read(), dtype=np.uint8)
    img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)

    if img is None:
        return {"error": "decode failed"}, 400

    if frame_queue.full():
        try:
            frame_queue.get_nowait()
        except queue.Empty:
            pass
    frame_queue.put(img)

    return {"status": "displayed"}, 200

def run_flask():
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False, threaded=True)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    cv2.namedWindow("received", cv2.WINDOW_NORMAL)

    try:
        while not stop_event.is_set():
            try:
                frame = frame_queue.get(timeout=0.1)
                cv2.imshow("received", frame)
            except queue.Empty:
                pass

            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                stop_event.set()
    finally:
        cv2.destroyAllWindows()
        for _ in range(4):
            cv2.waitKey(1)