import json
from urllib.request import Request, urlopen
import time
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone
import uuid
import argparse
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

    
    
    
parser = argparse.ArgumentParser()

parser.add_argument(
    "--model",
    required=True,
    choices=["deepseek-flash", "deepseek-v4-pro"]
)

parser.add_argument(
    "--price-period",
    required=True,
    choices=["peak", "offpeak"]
)

parser.add_argument(
    "--split",
    default="dev",
    choices=["dev", "test"]
)

parser.add_argument(
    "--repeat",
    type=int,
    default=1
)

args = parser.parse_args()

model_name = args.model
price_period = args.price_period
run_time = datetime.now(timezone.utc).isoformat(timespec="seconds")
run_id = uuid.uuid4().hex[:8]

with open(PROJECT_DIR / "apikey.txt", "r", encoding="utf-8") as f:
    api_key = f.read().strip()
RUBRIC_VERSION = "v0.1"
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
        "max_tokens": 1024,
        "temperature": 0,
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
            choice=result["choices"][0]
            answer = choice["message"]["content"]
            finish_reason=choice.get("finish_reason")
            usage = result.get("usage")
            return answer,usage,finish_reason

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
with open(PROJECT_DIR / "data" / "questions.jsonl", "r", encoding="utf-8") as file:
    result_dir = PROJECT_DIR / "runs"
    result_dir.mkdir(exist_ok=True)
    with open(result_dir / filename, "x", encoding="utf-8") as output:
        for line in file:
            if not line.strip():
                continue
            question = json.loads(line)
            if question['split']!=args.split:
                continue
            for trial in range(1,args.repeat+1):
                start = time.perf_counter()
                try:
                    answer, usage, finish_reason = askmodel(question["prompt"])

                    if finish_reason != "stop":
                        status = "incomplete"
                        error = f"finish_reason: {finish_reason}"

                    elif not isinstance(answer, str) or not answer.strip():
                        status = "incomplete"
                        error = "empty_answer"

                    else:
                        status = "success"
                        error = None

                except (HTTPError, URLError, TimeoutError) as e:
                    answer = None
                    usage = None
                    finish_reason = None
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
                    **question,
                        "model": model_name,
                        "runtime": run_time,
                        "run_id": run_id,
                        "latency": latency,
                        "answer": answer,
                        "status": status,
                        "error": error,
                        "usage": usage,
                        "cost": cost,
                        "finish_reason": finish_reason,
                        "temperature": 0,
                        "max_tokens": 1024,
                        "thinking": "disabled",
                        "price_period": price_period,
                        "currency": "CNY",
                        "trial": trial,
                        "rubric_version": RUBRIC_VERSION,
                }
                output.write(json.dumps(record, ensure_ascii=False) + "\n")
                print(question["id"], answer, status, error if error is not None else "没错误")

   