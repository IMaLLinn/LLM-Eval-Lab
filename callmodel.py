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
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                result = json.load(response)

            answer = result["choices"][0]["message"]["content"]
            return answer

        except HTTPError as e:
            if e.code not in (408, 429, 500, 502, 503, 504):
                raise

            if attempt == 2:
                raise

            print(f"HTTP {e.code}，2 秒后重试")

        except (URLError, TimeoutError) as e:
            if attempt == 2:
                raise

            print(f"网络请求失败：{e}，2 秒后重试")

        time.sleep(2)



with open("questions.jsonl", "r", encoding="utf-8") as file:
    with open("results.jsonl", "w", encoding="utf-8") as output:
        for line in file:
            question = json.loads(line)
            try:
                answer = askmodel(question["prompt"])
                status = "success"
                error = None
            except (HTTPError, URLError, TimeoutError) as e:
                answer = None
                status = "failed"
                error = str(e)
            record = {
                "id": question["id"],
                "prompt": question["prompt"],
                "expected": question["expected"],
                "answer":answer ,
                "status": status,
                "error": error
            }
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(question["id"], answer, status, error)

   