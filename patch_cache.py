with open('policy-ledger-v2/rag/cache/semantic_cache.py', 'r') as f:
    content = f.read()

repl_get = """            if not best_match:
                # 2. Cosine similarity scan (capped to recent entries)
                import time
                recent_keys = self.redis.zrevrange("vssc_index", 0, 499)
                for key_bytes in recent_keys:
                    k = f"vssc:{key_bytes.decode()}"
                    data = self.redis.get(k)
                    if data:
                        entry = json.loads(data)
                        if entry.get("allowed_depts") != dept_str or entry.get("is_diff_query") != is_diff_query:
                            continue
                        score = self._cosine_similarity(query_embedding, entry["embedding"])
                        if score > best_score:
                            best_score = score
                            best_match = entry
                            best_key = k"""

content = content.replace("""            if not best_match:
                # 2. Cosine similarity scan
                for k in self.redis.scan_iter("vssc:*"):
                    data = self.redis.get(k)
                    if data:
                        entry = json.loads(data)
                        if entry.get("allowed_depts") != dept_str or entry.get("is_diff_query") != is_diff_query:
                            continue
                        score = self._cosine_similarity(query_embedding, entry["embedding"])
                        if score > best_score:
                            best_score = score
                            best_match = entry
                            best_key = k""", repl_get)

repl_put = """        if self.use_redis:
            exact_hash = hashlib.sha256(np.array(query_embedding).tobytes()).hexdigest()
            exact_key = f"vssc_exact:{exact_hash}:{dept_str}:{is_diff_query}"
            self.redis.setex(exact_key, 86400, json.dumps(entry))
            
            key_id = exact_hash
            import time
            self.redis.zadd("vssc_index", {key_id: time.time()})
            self.redis.setex(f"vssc:{key_id}", 86400, json.dumps(entry))"""

content = content.replace("""        if self.use_redis:
            exact_hash = hashlib.sha256(np.array(query_embedding).tobytes()).hexdigest()
            exact_key = f"vssc_exact:{exact_hash}:{dept_str}:{is_diff_query}"
            self.redis.setex(exact_key, 86400, json.dumps(entry))
            
            key_id = exact_hash
            self.redis.setex(f"vssc:{key_id}", 86400, json.dumps(entry))""", repl_put)

with open('policy-ledger-v2/rag/cache/semantic_cache.py', 'w') as f:
    f.write(content)

