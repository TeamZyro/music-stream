import os
import requests
from flask import Flask, Response, request, jsonify
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# NOTE: API 2 MUST have the EXACT SAME SECRET_KEY as API 1 in its .env file.
# Otherwise it won't be able to decrypt the token sent from API 1.
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey123")

@app.route("/")
def health():
    return jsonify({
        "status": "online", 
        "node": "Zyro High-Speed Streaming Node (AWS)",
        "speed": "1-2 Gbps"
    }), 200

@app.route("/play/<token>")
def play_stream(token):
    """High Speed Proxy Node - Streams Data Directly to User using AWS Bandwidth"""
    s = URLSafeTimedSerializer(app.secret_key)
    
    try:
        # Decrypt token from API 1
        data = s.loads(token, salt="stream-proxy", max_age=86400)
    except SignatureExpired:
        return "Stream link expired (it lasts strictly 24 hours)", 410
    except BadSignature:
        return "Invalid or corrupted stream link.", 404
        
    url = data.get("u")
    stored_headers = data.get("h", {})
    
    req_headers = {}
    if 'User-Agent' in stored_headers: 
        req_headers['User-Agent'] = stored_headers['User-Agent']
    
    range_header = request.headers.get('Range', None)
    if range_header:
        req_headers['Range'] = range_header

    try:
        # Pinging googlevideo stream
        req = requests.get(url, headers=req_headers, stream=True, timeout=15)
        
        if req.status_code == 403:
            return "403 Forbidden. Google blocked the Node IP.", 403

        # Stream chunk by chunk super fast
        def generate():
            # Using 128KB chunks to utilize AWS 1-2Gbps High Speed pipe efficiently
            for chunk in req.iter_content(chunk_size=131072): 
                if chunk:
                    yield chunk

        rv = Response(generate(), status=req.status_code, content_type=req.headers.get('content-type', 'audio/mp4'))
        
        for key in ['Content-Range', 'Accept-Ranges', 'Content-Length']:
            if key in req.headers:
                rv.headers[key] = req.headers[key]

        return rv
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=True)
