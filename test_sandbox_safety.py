from agent import run_tests

print("Test 1: Infinite loop (should timeout, not hang)")
malicious_code = "while True:\n    pass"
passed, output = run_tests(malicious_code, "")
print(f"Result: {'Timed out safely' if 'TIMEOUT' in output else 'Ran (check output)'}")
print(output[:200])

print("\nTest 2: Trying to access network (should fail, no internet in container)")
network_code = """
import urllib.request
try:
    urllib.request.urlopen('http://google.com', timeout=3)
    print("NETWORK ACCESS SUCCEEDED - BAD!")
except Exception as e:
    print(f"Network blocked as expected: {e}")
"""
passed, output = run_tests(network_code, "")
print(output[:300])