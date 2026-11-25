import json
import math
import sys
from pathlib import Path

FILE = Path(__file__).resolve().parent.parent / "data" / "calibration.jsonl"


def load_cases():
    with FILE.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def save_cases(cases):
    temp = FILE.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")
    temp.replace(FILE)


def ask_label(message):
    while True:
        answer = input(message + " [1=通过, 0=不通过]: ").strip()
        if answer in ("0", "1"):
            return answer == "1"


def label():
    cases = load_cases()
    for case in cases:
        if case["human_content_pass"] is not None and case["human_format_pass"] is not None:
            continue

        print("\n", case["case_id"], case["id"])
        print("题目：", case["prompt"])
        print("参考答案：", case["expected"])
        print("评分标准：", case["rubric"])
        print("模型或构造回答：", case["answer"])
        print("格式要求：", case["format_spec"])

        if case["human_content_pass"] is None:
            case["human_content_pass"] = ask_label("内容是否满足全部 Rubric")
            save_cases(cases)
        if case["human_format_pass"] is None:
            case["human_format_pass"] = ask_label("格式是否合规（无特殊要求填1）")
            save_cases(cases)
    print("人工标注完成。")


def judge():
    from graderesult import grade_with_llm, grade_format, GRADER_VERSION, JUDGE_MODEL

    cases = load_cases()
    if any(c["human_content_pass"] is None or c["human_format_pass"] is None for c in cases):
        print("先完成人工标注，再运行 Judge。")
        return

    for case in cases:
        try:
            result = grade_with_llm(case)
            format_pass = grade_format(case)
            case["judge_content_pass"] = result["content_pass"]
            case["rule_format_pass"] = format_pass
            case["judge_reason"] = result["reason"]
            case["grader_version"] = GRADER_VERSION
            case["judge_model"] = JUDGE_MODEL
            case.pop("judge_error", None)
        except Exception as e:
            case["judge_error"] = str(e)
        save_cases(cases)
        print(case["case_id"], case.get("judge_content_pass"), case.get("judge_error", ""))


def wilson(k, n):
    z = 1.96
    p = k / n
    center = (p + z*z / (2*n)) / (1 + z*z/n)
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return center-half, center+half


def report():
    cases = load_cases()
    tp = tn = fp = fn = 0
    for c in cases:
        human = c.get("human_content_pass")
        judge = c.get("judge_content_pass")
        if type(human) is not bool or type(judge) is not bool:
            continue
        if human and judge:
            tp += 1
        elif not human and not judge:
            tn += 1
        elif judge:
            fp += 1
        else:
            fn += 1

    n = tp + tn + fp + fn
    print("总样本:", len(cases), "有效配对:", n, "未纳入:", len(cases)-n)
    if not n:
        return
    po = (tp + tn) / n
    pe = ((tp+fn)*(tp+fp) + (tn+fp)*(tn+fn)) / n**2
    print("混淆矩阵（人工为参考）")
    print("TP:", tp, "FP:", fp, "FN:", fn, "TN:", tn)
    print(f"一致率: {po:.2%}")
    if pe < 1:
        print(f"Cohen's Kappa: {(po-pe)/(1-pe):.4f}")
    else:
        print("Kappa: 无法计算（标签分布退化）")
    lo, hi = wilson(tp+tn, n)
    print(f"Wilson 95% 区间（假定样本独立，仅供描述）: [{lo:.2%}, {hi:.2%}]")
    for c in cases:
        h, j = c.get("human_content_pass"), c.get("judge_content_pass")
        if type(h) is bool and type(j) is bool and h != j:
            print("内容分歧:", c["case_id"], c["id"], h, j, c.get("judge_reason"))
        h, f = c.get("human_format_pass"), c.get("rule_format_pass")
        if type(h) is bool and type(f) is bool and h != f:
            print("格式分歧:", c["case_id"], c["id"], h, f)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("label", "judge", "report"):
        print("用法: python scripts/calibrate.py label|judge|report")
    elif sys.argv[1] == "label":
        label()
    elif sys.argv[1] == "judge":
        judge()
    else:
        report()
