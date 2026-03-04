import requests
import sys
url = "http://localhost:8000/process_video"
try:
    resp = requests.post(url, json={"url": "https://www.youtube.com/watch?v=s714-Xhly_k", "video_id": "test_3_web_1"}, timeout=30)
    print(resp.status_code)
    print(resp.text)
except Exception as e:
    print(e)
