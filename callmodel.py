import json
from getpass import getpass
from urllib.request import Request, urlopen
import time
from urllib.error import HTTPError, URLError

api_key = getpass("DeepSeek API key: ")


def askmodel(prompt):
    payload = {
        "model": "deepseek-flash",
        "messages": [{"role": "user", "content": prompt}],
        "thinking": {"type": "disabled"},
        "max_tokens": 64,
    }

    request = Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    answer = result["choices"][0]["message"]["content"]
    return answer



with open("questions.jsonl", "r", encoding="utf-8") as file:
    with open("results.jsonl", "w", encoding="utf-8") as output:
        for line in file:
            question = json.loads(line)
            answer = askmodel(question["prompt"])
            record = {
                "id": question["id"],
                "prompt": question["prompt"],
                "expected": question["expected"],
                "answer": answer
            }
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(question["id"], answer)

   