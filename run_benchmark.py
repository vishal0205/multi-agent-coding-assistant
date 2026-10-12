import time
import uuid

from tasks import TASKS
from graph_agent import solve_task_graph_persistent
from logger import save_task_result

def run_benchmark():
    summary = []
    run_id = uuid.uuid4().hex[:12]
    print(f"Running benchmark on {len(TASKS)} tasks...\n")

    for i, task in enumerate(TASKS, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(TASKS)}] {task['id']}")
        print(f"{'='*60}")

        start = time.time()
        checkpoint_id = f"benchmark_{run_id}_{task['id']}"
        result = solve_task_graph_persistent(
            task["description"],
            task_id=checkpoint_id,
        )
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