import json
import sys

def calculate(filename):
    groups = {}

    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)

            question_id = record["id"]
            result = record["grading"]["pass"]
            trial = record["trial"]

            if question_id not in groups:
                groups[question_id] = []

            groups[question_id].append((trial, result))

    total = 0
    correct = 0
    at3 = 0
    all3 = 0

    for trials in groups.values():
        if sorted(t[0] for t in trials) != [1, 2, 3]:
            continue

        results = [t[1] for t in trials]

        if None in results:
            continue

        total += 1
        correct += sum(results)

        if any(results):
            at3 += 1

        if all(results):
            all3 += 1

    print("题目总数：", len(groups))
    print("有效题目数：", total)
    print("未纳入统计：", len(groups) - total)

    if total > 0:
        print(f"pass@1: {correct / (total * 3):.2%}")
        print(f"pass@3: {at3 / total:.2%}")
        print(f"pass^3: {all3 / total:.2%}")

if __name__ == "__main__":
    calculate(sys.argv[1])