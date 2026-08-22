with open('policy-ledger-v2/rag/vectordb/chroma.py', 'r') as f:
    content = f.read()

repl = """def _get_client():
    try:
        import chromadb
        chroma_host = os.environ.get("CHROMA_HOST")
        chroma_port = int(os.environ.get("CHROMA_PORT", 8001))
        if chroma_host and chroma_host not in ("localhost", "127.0.0.1"):
            # Use HTTP client for remote/dockerized ChromaDB
            return chromadb.HttpClient(host=chroma_host, port=chroma_port)
        # Fall back to embedded persistent client
        os.makedirs(CHROMA_PATH, exist_ok=True)
        return chromadb.PersistentClient(path=CHROMA_PATH)
    except ImportError:"""

content = content.replace("""def _get_client():
    try:
        import chromadb
        os.makedirs(CHROMA_PATH, exist_ok=True)
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        return client
    except ImportError:""", repl)

with open('policy-ledger-v2/rag/vectordb/chroma.py', 'w') as f:
    f.write(content)

