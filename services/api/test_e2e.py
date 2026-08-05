import time
import json
import urllib.request
import urllib.parse
import mimetypes
from PIL import Image

def encode_multipart_formdata(fields, files):
    boundary = b"----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = bytearray()
    
    for key, value in fields.items():
        body.extend(b"--" + boundary + b"\r\n")
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode('utf-8'))
        body.extend(value.encode('utf-8') + b"\r\n")
        
    for key, (filename, file_content, mime_type) in files.items():
        body.extend(b"--" + boundary + b"\r\n")
        body.extend(f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'.encode('utf-8'))
        body.extend(f'Content-Type: {mime_type}\r\n\r\n'.encode('utf-8'))
        body.extend(file_content + b"\r\n")
        
    body.extend(b"--" + boundary + b"--\r\n")
    return body, b"multipart/form-data; boundary=" + boundary

# 1. Create a dummy test image
img = Image.new("RGB", (100, 100), color="red")
img.save("test_image.jpg")

# 2. Submit it to the API
print("Submitting image to API...")
with open("test_image.jpg", "rb") as f:
    file_content = f.read()

fields = {"input": "Check this image", "preferredLanguage": "en"}
files = {"file": ("test_image.jpg", file_content, "image/jpeg")}

body, content_type = encode_multipart_formdata(fields, files)

req = urllib.request.Request("http://localhost:4000/api/v1/analyses", data=body, method="POST")
req.add_header("Content-Type", content_type.decode("utf-8"))

try:
    with urllib.request.urlopen(req) as response:
        print(f"POST Status: {response.status}")
        data = json.loads(response.read().decode("utf-8"))
        print("POST Response:", data)
        analysis_id = data.get("id")

    if analysis_id:
        print(f"\nPolling analysis ID: {analysis_id}")
        for _ in range(5):
            time.sleep(1.0)
            poll_req = urllib.request.Request(f"http://localhost:4000/api/v1/analyses/{analysis_id}")
            with urllib.request.urlopen(poll_req) as poll_resp:
                poll_data = json.loads(poll_resp.read().decode("utf-8"))
                print(f"Status: {poll_data.get('status')}, Progress: {poll_data.get('progress')}")
                if poll_data.get("status") in ["COMPLETED", "FAILED"]:
                    break
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code} {e.reason}")
    print(e.read().decode("utf-8"))

# 4. Fetch the Media Forensics Result directly (using internal service for testing)
print("\nFetching Media Forensics Results...")
import sqlite3
import os

# Since there's no public endpoint yet, let's just show you how you would test the model on a real image via the python interface:
