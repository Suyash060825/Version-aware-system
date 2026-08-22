def compute_chunk_hash(text: str, model_name: str, model_version: str) -> str:
    import hashlib
    content = f"{text}|{model_name}|{model_version}"
    return hashlib.sha256(content.encode()).hexdigest()