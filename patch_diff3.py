with open('policy-ledger-v2/rag/chatbot/chat_service.py', 'r') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if line.startswith("def _run_diff_agent("):
        start_idx = i
        break

if start_idx != -1:
    for i in range(start_idx + 1, len(lines)):
        if lines[i].startswith("def answer("):
            end_idx = i - 1
            break

if start_idx != -1 and end_idx != -1:
    new_lines = []
    new_lines.append(lines[start_idx])
    new_lines.append("    try:\n")
    for i in range(start_idx + 1, end_idx):
        if lines[i] == "\n":
            new_lines.append(lines[i])
        else:
            new_lines.append("    " + lines[i])
    new_lines.append("    except Exception as e:\n")
    new_lines.append("        import logging\n")
    new_lines.append("        logging.error(f'[DiffAgent] Error: {e}')\n")
    new_lines.append("        return None\n\n")
    
    final_lines = lines[:start_idx] + new_lines + lines[end_idx:]
    with open('policy-ledger-v2/rag/chatbot/chat_service.py', 'w') as f:
        f.writelines(final_lines)

