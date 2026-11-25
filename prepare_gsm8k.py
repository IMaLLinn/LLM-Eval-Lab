import json
import random
from urllib.request import urlopen

BASE_URL = (
    "https://raw.githubusercontent.com/openai/"
    "grade-school-math/master/grade_school_math/data/"
)

random.seed(42)

with open("questions.jsonl", "a", encoding="utf-8") as f:
    for source, split, count in [
        ("train", "dev", 10),
        ("test", "test", 20)
    ]:
        with urlopen(BASE_URL + source + ".jsonl") as response:
            lines = response.read().decode("utf-8").splitlines()

        for i in random.sample(range(len(lines)), count):
            item = json.loads(lines[i])

            record = {
                "id": f"gsm8k-{source}-{i}",
                "category": "benchmark",
                "split": split,
                "origin": "GSM8K",
                "review_status": "pending_manual_review",
                "grader_type": "numeric",
                "prompt": item["question"] + "\nOutput only the final number.",
                "expected": item["answer"].split("####")[-1].strip().replace(",", "")
            }

            f.write(json.dumps(record, ensure_ascii=False) + "\n")