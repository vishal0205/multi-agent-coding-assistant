def solution(a, b):
    return a + b

assert solution(1, 2) == 3
assert solution(-5, 5) == 0
assert solution(0, 0) == 0
assert solution(123456789, 987654321) == 1111111110
assert solution(1.5, 2.5) == 4.0
print("ALL TESTS PASSED")