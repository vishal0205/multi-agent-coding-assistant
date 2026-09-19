import time
from tasks import TASKS
from agent import solve_task
from logger import save_task_result

def run_benchmark():
    summary = []
    print(f"Running benchmark on {len(TASKS)} tasks...\n")

    for i, task in enumerate(TASKS, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(TASKS)}] {task['id']}")
        print(f"{'='*60}")

        start = time.time()
        result = solve_task(task["description"])
        duration = time.time() - start

        save_task_result(task["id"], task["description"], result)

        summary.append({
            "id": task["id"],
            "success": result["success"],
            "attempts": result["attempts"],
            "duration_sec": round(duration, 1)
        })

    print(f"\n\n{'='*60}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*60}")
    passed = sum(1 for r in summary if r["success"])
    total_attempts = sum(r["attempts"] for r in summary)
    avg_attempts = total_attempts / len(summary)

    for r in summary:
        status = "PASS" if r["success"] else "FAIL"
        print(f"  [{status}] {r['id']} — {r['attempts']} attempt(s), {r['duration_sec']}s")

    print(f"\nTotal: {passed}/{len(summary)} tasks solved")
    print(f"Average attempts per task: {avg_attempts:.1f}")

if __name__ == "__main__":
    run_benchmark()