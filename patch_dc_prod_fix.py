import re

with open('policy-ledger-v2/docker-compose.prod.yml', 'r') as f:
    content = f.read()

# Fix the extra_hosts placement. It should be in web, not in nginx.
# Let's just do a manual replace.
content = content.replace("""    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      web:""", """    depends_on:
      web:""")

content = content.replace("""    depends_on:
      postgres:""", """    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      postgres:""", 1)

with open('policy-ledger-v2/docker-compose.prod.yml', 'w') as f:
    f.write(content)
