with open('policy-ledger-v2/nginx/nginx.conf', 'r') as f:
    content = f.read()

repl = """        location /rag/api/chat {
            limit_req zone=api_limit burst=5 nodelay;
            proxy_pass http://flask_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 600s;      # match gunicorn timeout
            proxy_connect_timeout 10s;
            proxy_send_timeout 600s;
            proxy_buffering off;
            proxy_cache off;
            proxy_set_header Connection '';
            chunked_transfer_encoding on;
        }"""

import re
content = re.sub(
    r'        location /rag/api/chat \{.*?proxy_read_timeout 120s;\n        \}',
    repl,
    content,
    flags=re.DOTALL
)

with open('policy-ledger-v2/nginx/nginx.conf', 'w') as f:
    f.write(content)

