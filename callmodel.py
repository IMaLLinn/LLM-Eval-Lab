import json
from getpass import getpass
from urllib.request import Request, urlopen
import time
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone
import uuid
import argparse

    
    
    
parser = argparse.ArgumentParser()
parser.add_argument(
    "--model",
    required=False,
    choices=["deepseek-flash", "deepseek-v4-pro"]
)
parser.add_argument(
    "--price-period",
    required=False,
    choices=["peak", "offpeak"]
)
args = parser.parse_args()

model_name = args.model
price_period = args.price_period
run_time = datetime.now(timezone.utc).isoformat(timespec="seconds")
run_id = uuid.uuid4().hex[:8]

api_key = getpass("DeepSeek API key: ")

PRICES = {
    "deepseek-flash": {
        "offpeak": (0.02, 1.0, 4.0),
        "peak": (0.04, 2.0, 8.0)
    },
    "deepseek-v4-pro": {
        "offpeak": (0.15, 4.5, 13.5),
        "peak": (0.30, 9.0, 27.0)
    }
}

def askmodel(prompt):
    payload = {
        "model": model_name,
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
            usage = result.get("usage")
            return answer,usage

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


filename= f'{model_name}results_{run_id}.jsonl'
with open("questions.jsonl", "r", encoding="utf-8") as file:
    with open(filename, "x", encoding="utf-8") as output:
        for line in file:
            if not line.strip():
                continue
            question = json.loads(line)
            start = time.perf_counter()
            try:
                answer, usage = askmodel(question["prompt"])
                status = "success"
                error = None
            except (HTTPError, URLError, TimeoutError) as e:
                answer = None
                usage = None
                status = "failed"
                error = str(e)
            latency = round(time.perf_counter() - start, 3)
            cost = None
            if isinstance(usage, dict):
                hit = usage.get("prompt_cache_hit_tokens")
                miss = usage.get("prompt_cache_miss_tokens")
                output_tokens = usage.get("completion_tokens")

                if all(isinstance(x, int) and x >= 0 for x in (hit, miss, output_tokens)):
                    hit_price, miss_price, output_price = PRICES[model_name][price_period]
                    cost = (
                        hit * hit_price
                        + miss * miss_price
                        + output_tokens * output_price
                    ) / 1_000_000
            record = {
                "id": question["id"],
                "prompt": question["prompt"],
                "expected": question["expected"],
                "model": model_name,
                "runtime": run_time,
                "run_id": run_id,
                "latency": latency,
                "answer":answer ,
                "status": status,
                "error": error,
                "usage": usage,
                "cost": cost
            }
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(question["id"], answer, status, error if error is not None else "没错误")

   