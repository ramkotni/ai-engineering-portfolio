# 🐍 Python Practice Questions for the Karat Interview (Easy + Medium)

> 130+ questions with a short **explanation** and a **runnable Python solution** for each.
> Covers Python fundamentals, strings, lists, dicts/sets, functions, OOP, iterators/generators/decorators,
> exceptions & files, the standard library, and Karat-style coding problems (log parsing, intervals, grids, graphs, DP).

**How to use this guide**
- Cover the code, try the question yourself in an editor, then compare.
- Karat interviews are typically a live session: a few short Python knowledge questions followed by 1–2 coding problems that get harder in steps. Practise **talking while you code**: restate the problem, give an example, say the complexity, test edge cases.
- Every code block is self-contained and runnable (Python 3.9+). Outputs are shown as `# comment`.
- Difficulty tags: 🟢 Easy · 🟡 Medium.

**Interview habits that score points**
1. Clarify input/output and edge cases (empty input, duplicates, negatives, one element).
2. Start with a simple correct solution, then optimize.
3. State time and space complexity (Big-O).
4. Name variables clearly; keep functions small.
5. Test with your own examples before saying "done".

---

## 📑 Table of Contents

1. [Python Fundamentals](#1-python-fundamentals) (Q1–Q12)
2. [Strings](#2-strings) (Q13–Q28)
3. [Lists & Tuples](#3-lists--tuples) (Q29–Q46)
4. [Dictionaries & Sets](#4-dictionaries--sets) (Q47–Q62)
5. [Control Flow, Functions & Recursion](#5-control-flow-functions--recursion) (Q63–Q76)
6. [Object-Oriented Programming](#6-object-oriented-programming) (Q77–Q87)
7. [Iterators, Generators, Decorators & Context Managers](#7-iterators-generators-decorators--context-managers) (Q88–Q97)
8. [Exceptions & File Handling](#8-exceptions--file-handling) (Q98–Q105)
9. [Standard Library & Python Knowledge](#9-standard-library--python-knowledge) (Q106–Q115)
10. [Karat-Style Algorithm & Data-Processing Problems](#10-karat-style-algorithm--data-processing-problems) (Q116–Q140)

Appendix: [Big-O cheat-sheet](#-big-o-cheat-sheet) · [Final checklist](#-final-checklist)

---
---

# 1. Python Fundamentals

### Q1. What is the difference between mutable and immutable types? 🟢
**Explanation:** Immutable objects (`int`, `float`, `str`, `tuple`, `frozenset`, `bytes`) cannot change after creation; "changing" them creates a new object. Mutable objects (`list`, `dict`, `set`) can change in place, so two names pointing to the same object see each other's changes.

```python
a = [1, 2]
b = a              # b and a are the SAME list
b.append(3)
print(a)           # [1, 2, 3]

t = (1, 2)
try:
    t[0] = 9
except TypeError as e:
    print(e)       # 'tuple' object does not support item assignment

s = "hi"
s2 = s.upper()     # creates a new string
print(s, s2)       # hi HI
```

---

### Q2. What is the difference between `is` and `==`? 🟢
**Explanation:** `==` compares **values**; `is` compares **identity** (same object in memory). Use `is` only for singletons such as `None`, `True`, `False`.

```python
a = [1, 2]
b = [1, 2]
c = a
print(a == b)      # True   (same values)
print(a is b)      # False  (different objects)
print(c is a)      # True   (same object)

x = None
print(x is None)   # True   (correct way to test for None)
```

---

### Q3. Swap two variables without a temporary variable. 🟢
**Explanation:** Python evaluates the right side first as a tuple, then unpacks it.

```python
a, b = 1, 2
a, b = b, a
print(a, b)        # 2 1
```

---

### Q4. How do `//`, `%`, `/`, `**` and `divmod` behave (including negatives)? 🟢
**Explanation:** `//` is **floor** division (rounds toward negative infinity), so `-7 // 2` is `-4`, not `-3`. `%` always takes the sign of the divisor, and `a == (a // b) * b + a % b` always holds.

```python
print(7 // 2)         # 3
print(-7 // 2)        # -4
print(-7 % 2)         # 1
print(7 / 2)          # 3.5
print(2 ** 10)        # 1024
print(divmod(17, 5))  # (3, 2)
```

---

### Q5. Which values are falsy in Python? 🟢
**Explanation:** Falsy: `0`, `0.0`, `""`, `[]`, `{}`, `()`, `set()`, `None`, `False`. Everything else is truthy — including the string `"0"` and the list `[0]`. This lets you write `if items:` instead of `if len(items) > 0:`.

```python
values = (0, 0.0, "", [], {}, None, "0", [0])
print([bool(v) for v in values])
# [False, False, False, False, False, False, True, True]

items = []
if not items:
    print("empty")   # empty
```

---

### Q6. Why does `0.1 + 0.2 == 0.3` return `False`? How do you compare floats safely? 🟢
**Explanation:** Floats are stored in binary, and 0.1 cannot be represented exactly. Compare with a tolerance (`math.isclose`) or use `decimal.Decimal` for money.

```python
import math
from decimal import Decimal

print(0.1 + 0.2)                      # 0.30000000000000004
print(0.1 + 0.2 == 0.3)               # False
print(math.isclose(0.1 + 0.2, 0.3))   # True
print(Decimal("0.1") + Decimal("0.2"))  # 0.3
```

---

### Q7. How do type conversions work (`int`, `float`, `str`, `round`)? 🟢
**Explanation:** `int()` truncates toward zero. `round()` uses **banker's rounding** (ties go to the nearest even number).

```python
print(int("42"))         # 42
print(int(3.9))          # 3
print(int(-3.9))         # -3
print(round(2.5))        # 2
print(round(3.5))        # 4
print(round(3.14159, 2)) # 3.14
print(float("1e3"))      # 1000.0
print(str(10) + "1")     # 101
print(list("abc"))       # ['a', 'b', 'c']
```

---

### Q8. What is the mutable default argument pitfall? 🟡
**Explanation:** Default values are evaluated **once**, when the function is defined. A mutable default (like `[]`) is then shared across calls. Use `None` as the default and create the list inside.

```python
def bad(x, acc=[]):
    acc.append(x)
    return acc

print(bad(1))   # [1]
print(bad(2))   # [1, 2]   <-- surprise! same list reused

def good(x, acc=None):
    if acc is None:
        acc = []
    acc.append(x)
    return acc

print(good(1))  # [1]
print(good(2))  # [2]
```

---

### Q9. What are `*args` and `**kwargs`? 🟢
**Explanation:** `*args` collects extra positional arguments into a tuple; `**kwargs` collects extra keyword arguments into a dict. The same `*` / `**` syntax at the call site unpacks a list/dict into arguments.

```python
def f(a, *args, sep="-", **kwargs):
    return a, args, sep, kwargs

print(f(1, 2, 3, sep="+", x=9))   # (1, (2, 3), '+', {'x': 9})

def add(a, b, c):
    return a + b + c

nums = [1, 2, 3]
print(add(*nums))                          # 6
print(add(**{"a": 1, "b": 2, "c": 3}))     # 6
```

---

### Q10. Explain shallow copy vs deep copy. 🟡
**Explanation:** A shallow copy duplicates the outer container but **shares** the inner objects. A deep copy recursively duplicates everything. Slicing `a[:]`, `list(a)` and `a.copy()` are all shallow.

```python
import copy

orig = [[1, 2], [3]]
shallow = copy.copy(orig)
deep = copy.deepcopy(orig)

orig[0].append(99)
print(shallow)       # [[1, 2, 99], [3]]  (inner list is shared)
print(deep)          # [[1, 2], [3]]      (fully independent)
print(orig[:] is orig)   # False  (new outer list, but still shallow)
```

---

### Q11. Explain variable scope (LEGB) and `global` / `nonlocal`. 🟡
**Explanation:** Python looks up names in order: **L**ocal → **E**nclosing → **G**lobal → **B**uilt-in. Assigning to a name inside a function makes it local unless you declare it `global` or `nonlocal`.

```python
x = "global"

def outer():
    x = "enclosing"
    def inner():
        nonlocal x          # modify the enclosing x
        x = "changed by inner"
    inner()
    return x

print(outer())   # changed by inner
print(x)         # global

counter = 0
def inc():
    global counter
    counter += 1

inc(); inc()
print(counter)   # 2
```

---

### Q12. How do chained comparisons and short-circuit `and` / `or` work? 🟢
**Explanation:** `1 < x < 10` is valid and means `1 < x and x < 10`. `or` returns the first truthy operand, `and` returns the first falsy operand (or the last one) — they return **values**, not just `True`/`False`.

```python
x = 5
print(1 < x < 10)         # True
print(0 or "default")     # default
print("a" and "b")        # b
print(None or [] or "last")  # last

name = None
print(name and name.upper())  # None  (safe: upper() never called)
```

---
---

# 2. Strings

### Q13. Reverse a string. 🟢
**Explanation:** Strings are immutable, so build a new one. Slicing with step `-1` is the idiomatic way. O(n).

```python
s = "interview"
print(s[::-1])                 # weivretni
print("".join(reversed(s)))    # weivretni

# manual loop
out = ""
for ch in s:
    out = ch + out
print(out)                     # weivretni
```

---

### Q14. Check whether a string is a palindrome (ignore case, spaces and punctuation). 🟢
**Explanation:** Keep only alphanumeric characters, lower-case them, compare with the reverse. A two-pointer version avoids creating a second string (O(1) extra space).

```python
def is_palindrome(s):
    cleaned = [c.lower() for c in s if c.isalnum()]
    return cleaned == cleaned[::-1]

print(is_palindrome("A man, a plan, a canal: Panama"))  # True
print(is_palindrome("race a car"))                       # False

def is_palindrome_two_pointer(s):
    i, j = 0, len(s) - 1
    while i < j:
        if not s[i].isalnum():
            i += 1
        elif not s[j].isalnum():
            j -= 1
        elif s[i].lower() != s[j].lower():
            return False
        else:
            i += 1
            j -= 1
    return True

print(is_palindrome_two_pointer("No 'x' in Nixon"))      # True
```

---

### Q15. Count the vowels in a string. 🟢
**Explanation:** `sum()` over a generator of booleans (`True` counts as 1).

```python
def count_vowels(s):
    return sum(ch in "aeiou" for ch in s.lower())

print(count_vowels("Hello World"))   # 3
```

---

### Q16. Count the frequency of each character. 🟢
**Explanation:** Use a dict by hand, or `collections.Counter`. Both are O(n).

```python
from collections import Counter

s = "banana"
freq = {}
for ch in s:
    freq[ch] = freq.get(ch, 0) + 1
print(freq)                          # {'b': 1, 'a': 3, 'n': 2}

print(Counter(s).most_common(1))     # [('a', 3)]
```

---

### Q17. Find the first non-repeating character. 🟢
**Explanation:** First pass counts characters; second pass returns the first with count 1. O(n).

```python
from collections import Counter

def first_unique(s):
    counts = Counter(s)
    for ch in s:
        if counts[ch] == 1:
            return ch
    return None

print(first_unique("swiss"))   # w
print(first_unique("aabb"))    # None
```

---

### Q18. Check whether two strings are anagrams. 🟢
**Explanation:** Anagrams have the same letters with the same counts. Sorting is O(n log n); `Counter` is O(n).

```python
from collections import Counter

def is_anagram(a, b):
    return Counter(a.lower()) == Counter(b.lower())

print(is_anagram("Listen", "Silent"))   # True
print(is_anagram("abc", "abd"))         # False
print(sorted("listen") == sorted("silent"))  # True
```

---

### Q19. Parse a CSV-style line and use `split`, `join`, `strip`. 🟢
**Explanation:** `split()` with no argument splits on any whitespace and drops empties; `split(",", 1)` limits the number of splits.

```python
line = "alice,30,NYC"
name, age, city = line.split(",")
print(name, int(age), city)          # alice 30 NYC

print("  a   b  ".split())            # ['a', 'b']
print("a,b,,c".split(","))            # ['a', 'b', '', 'c']
print("k=v=w".split("=", 1))          # ['k', 'v=w']
print("-".join(["2024", "05", "01"])) # 2024-05-01
print("  padded  ".strip())            # padded
```

---

### Q20. Show common f-string formatting (width, precision, commas, percent). 🟢
**Explanation:** Format spec after the colon: `:.2f` (2 decimals), `:05d` (zero-pad), `:,` (thousands), `:.1%` (percent), `:>6` / `:<6` / `:^7` (align).

```python
name, pi, x = "Ann", 3.14159, 5
print(f"{pi:.2f}")        # 3.14
print(f"{42:05d}")        # 00042
print(f"{1234567:,}")     # 1,234,567
print(f"{0.256:.1%}")     # 25.6%
print(f"{name:>6}|")      #    Ann|
print(f"{name:<6}|")      # Ann   |
print(f"{name:^7}|")      #   Ann  |
print(f"{x=}")            # x=5
```

---

### Q21. Remove duplicate characters but keep the original order. 🟢
**Explanation:** Dicts keep insertion order (3.7+), so `dict.fromkeys` removes duplicates in order. A plain `set` would lose order.

```python
s = "programming"
print("".join(dict.fromkeys(s)))   # progamin
```

---

### Q22. Capitalize each word / change case. 🟢
**Explanation:** `title()` capitalizes every word, `capitalize()` only the first character of the string.

```python
s = "hello wORLD"
print(s.title())        # Hello World
print(s.capitalize())   # Hello world
print(s.swapcase())     # HELLO World
print(s.upper())        # HELLO WORLD
print(" ".join(w.capitalize() for w in s.split()))  # Hello World
```

---

### Q23. Check if a string is numeric and convert safely. 🟢
**Explanation:** `isdigit()` only accepts digits (no sign, no decimal point). Safer: try `int()` and catch `ValueError` (EAFP: "easier to ask forgiveness than permission").

```python
def to_int(s, default=None):
    try:
        return int(s.strip())
    except ValueError:
        return default

print("12".isdigit(), "-12".isdigit(), "1.5".isdigit())  # True False False
print(to_int(" 42 "))   # 42
print(to_int("4x2"))    # None
```

---

### Q24. Find the longest word in a sentence. 🟢
**Explanation:** `max(..., key=len)`. On ties, the first one wins.

```python
sentence = "the quick brown fox jumped"
print(max(sentence.split(), key=len))   # jumped
```

---

### Q25. Compress a string: `aaabbc` → `a3b2c1` (and decompress). 🟡
**Explanation:** `itertools.groupby` groups consecutive equal characters. Decompress with a regex that repeats each character.

```python
import re
from itertools import groupby

def compress(s):
    return "".join(f"{ch}{len(list(group))}" for ch, group in groupby(s))

def decompress(s):
    return re.sub(r"(\D)(\d+)", lambda m: m.group(1) * int(m.group(2)), s)

enc = compress("aaabbc")
print(enc)               # a3b2c1
print(decompress(enc))   # aaabbc
```

---

### Q26. Implement a Caesar cipher. 🟡
**Explanation:** Shift letters by `k` using modular arithmetic, keep case, leave non-letters alone.

```python
def caesar(text, k):
    out = []
    for ch in text:
        if ch.isalpha():
            base = ord("A") if ch.isupper() else ord("a")
            out.append(chr((ord(ch) - base + k) % 26 + base))
        else:
            out.append(ch)
    return "".join(out)

secret = caesar("Hello, World!", 3)
print(secret)                # Khoor, Zruog!
print(caesar(secret, -3))    # Hello, World!
```

---

### Q27. Find the longest common prefix of a list of strings. 🟡
**Explanation:** `zip(*strs)` yields the i-th characters of all strings together; stop when they are not all equal.

```python
def longest_common_prefix(strs):
    prefix = []
    for chars in zip(*strs):
        if len(set(chars)) != 1:
            break
        prefix.append(chars[0])
    return "".join(prefix)

print(longest_common_prefix(["flower", "flow", "flight"]))  # fl
print(repr(longest_common_prefix(["dog", "car"])))           # ''
```

---

### Q28. Count the words in a text, ignoring case and punctuation. 🟡
**Explanation:** Extract words with a regex, then count with `Counter`.

```python
import re
from collections import Counter

text = "The cat and the hat. The end!"
words = re.findall(r"[a-z']+", text.lower())
print(words)                              # ['the', 'cat', 'and', 'the', 'hat', 'the', 'end']
print(Counter(words).most_common(2))      # [('the', 3), ('cat', 1)]
```

---
---

# 3. Lists & Tuples

### Q29. Show the most common list methods. 🟢
**Explanation:** `append` adds one item, `extend` adds many, `insert(i, x)` adds at an index (O(n)), `pop()` removes the last (O(1)), `pop(0)` removes the first (O(n)), `remove(x)` removes the first match.

```python
a = [1, 2, 3]
a.append(4)
a.extend([5, 6])
a.insert(0, 0)
print(a)            # [0, 1, 2, 3, 4, 5, 6]
print(a.pop())      # 6
print(a.pop(0))     # 0
a.remove(3)
print(a)            # [1, 2, 4, 5]
print(a.index(4))   # 2
print(a.count(1))   # 1
del a[0]
print(a)            # [2, 4, 5]
```

---

### Q30. Demonstrate slicing tricks. 🟢
**Explanation:** `a[start:stop:step]`; `stop` is excluded; negative indexes count from the end; slicing never raises `IndexError`.

```python
a = list(range(10))
print(a[2:5])     # [2, 3, 4]
print(a[:3])      # [0, 1, 2]
print(a[-3:])     # [7, 8, 9]
print(a[::2])     # [0, 2, 4, 6, 8]
print(a[::-1])    # [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
print(a[1:-1])    # [1, 2, 3, 4, 5, 6, 7, 8]
print(a[20:])     # []
```

---

### Q31. What is the difference between `list.reverse()`, `reversed()`, `[::-1]` and `sorted(reverse=True)`? 🟢
**Explanation:** `reverse()` works in place and returns `None`. `reversed()` returns an iterator. `[::-1]` returns a new reversed list. `sorted(..., reverse=True)` sorts descending (not the same as reversing!).

```python
a = [3, 1, 2]
print(a[::-1])                 # [2, 1, 3]
print(list(reversed(a)))       # [2, 1, 3]
print(sorted(a, reverse=True)) # [3, 2, 1]
print(a.reverse())             # None
print(a)                       # [2, 1, 3]
```

---

### Q32. Remove duplicates from a list. 🟢
**Explanation:** `set` removes duplicates but loses order; `dict.fromkeys` keeps first-seen order.

```python
nums = [3, 1, 3, 2, 1]
print(sorted(set(nums)))              # [1, 2, 3]
print(list(dict.fromkeys(nums)))      # [3, 1, 2]
```

---

### Q33. Find the second largest distinct number in one pass. 🟢
**Explanation:** Track the two best values while scanning. O(n) time, O(1) space.

```python
def second_largest(nums):
    first = second = float("-inf")
    for n in nums:
        if n > first:
            first, second = n, first
        elif first > n > second:
            second = n
    return None if second == float("-inf") else second

print(second_largest([5, 1, 9, 9, 7]))  # 7
print(second_largest([4, 4]))           # None
```

---

### Q34. Flatten a nested list. 🟡
**Explanation:** One level can be done with a nested comprehension; arbitrary depth needs recursion.

```python
def flatten(items):
    out = []
    for it in items:
        if isinstance(it, list):
            out.extend(flatten(it))
        else:
            out.append(it)
    return out

print(flatten([1, [2, [3, [4]], 5], 6]))   # [1, 2, 3, 4, 5, 6]
print([x for sub in [[1, 2], [3], [4, 5]] for x in sub])  # [1, 2, 3, 4, 5]
```

---

### Q35. Rotate a list to the right by `k` places. 🟡
**Explanation:** Use `k % n` so large `k` wraps around, then join two slices.

```python
def rotate_right(a, k):
    if not a:
        return a
    k %= len(a)
    return a[-k:] + a[:-k]

print(rotate_right([1, 2, 3, 4, 5], 2))    # [4, 5, 1, 2, 3]
print(rotate_right([1, 2, 3, 4, 5], 7))    # [4, 5, 1, 2, 3]
print(rotate_right([1, 2, 3], 0))          # [1, 2, 3]
```

---

### Q36. Move all zeros to the end, keeping the order of the other elements (in place). 🟡
**Explanation:** Two pointers: `w` is where the next non-zero belongs. O(n) time, O(1) space.

```python
def move_zeros(a):
    w = 0
    for r in range(len(a)):
        if a[r] != 0:
            a[w], a[r] = a[r], a[w]
            w += 1
    return a

print(move_zeros([0, 1, 0, 3, 12]))   # [1, 3, 12, 0, 0]
```

---

### Q37. Two Sum: return the indices of two numbers that add up to a target. 🟢
**Explanation:** Brute force is O(n²). A dict of `value → index` makes it O(n): for each number look for `target - n`.

```python
def two_sum(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        if target - n in seen:
            return seen[target - n], i
        seen[n] = i
    return None

print(two_sum([2, 7, 11, 15], 9))   # (0, 1)
print(two_sum([3, 2, 4], 6))        # (1, 2)
print(two_sum([1, 2], 10))          # None
```

---

### Q38. Maximum subarray sum (Kadane's algorithm). 🟡
**Explanation:** At each element, either extend the current subarray or start fresh. O(n).

```python
def max_subarray(nums):
    best = cur = nums[0]
    for n in nums[1:]:
        cur = max(n, cur + n)
        best = max(best, cur)
    return best

print(max_subarray([-2, 1, -3, 4, -1, 2, 1, -5, 4]))   # 6
print(max_subarray([-3, -1, -2]))                      # -1
```

---

### Q39. Merge two sorted lists into one sorted list. 🟢
**Explanation:** Two pointers, always take the smaller front element. O(n + m). The standard library has `heapq.merge` for this too.

```python
import heapq

def merge_sorted(a, b):
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            out.append(a[i]); i += 1
        else:
            out.append(b[j]); j += 1
    out.extend(a[i:])
    out.extend(b[j:])
    return out

print(merge_sorted([1, 3, 5], [2, 4, 6, 8]))          # [1, 2, 3, 4, 5, 6, 8]
print(list(heapq.merge([1, 3, 5], [2, 4, 6, 8])))     # [1, 2, 3, 4, 5, 6, 8]
```

---

### Q40. Sort with a custom key (multi-level, descending, case-insensitive). 🟡
**Explanation:** `key=` returns what to compare. Python's sort is **stable**, so equal keys keep their original order. Return a tuple to sort by several fields.

```python
people = [("Bob", 25), ("alice", 30), ("Cara", 25)]

print(sorted(people, key=lambda p: (p[1], p[0].lower())))
# [('Bob', 25), ('Cara', 25), ('alice', 30)]

print(sorted(people, key=lambda p: -p[1]))
# [('alice', 30), ('Bob', 25), ('Cara', 25)]   (ties keep original order)

print(sorted(["b", "A", "c"], key=str.lower))   # ['A', 'b', 'c']
```

---

### Q41. Show list comprehension patterns (filter, if/else, nested, transpose). 🟢
**Explanation:** `[expr for x in it if cond]`. For if/else the conditional goes **before** the `for`.

```python
print([x * x for x in range(10) if x % 2 == 0])          # [0, 4, 16, 36, 64]
print(["even" if x % 2 == 0 else "odd" for x in range(4)])  # ['even', 'odd', 'even', 'odd']
print([(i, j) for i in range(2) for j in range(2)])      # [(0, 0), (0, 1), (1, 0), (1, 1)]

matrix = [[1, 2, 3], [4, 5, 6]]
print([list(row) for row in zip(*matrix)])               # [[1, 4], [2, 5], [3, 6]]
```

---

### Q42. Explain tuple unpacking, star-unpacking and `namedtuple`. 🟢
**Explanation:** Tuples are immutable sequences. `*rest` captures "the remaining items". A one-element tuple needs a trailing comma. `namedtuple` gives readable field names.

```python
from collections import namedtuple

first, *middle, last = [1, 2, 3, 4, 5]
print(first, middle, last)          # 1 [2, 3, 4] 5

print(type((1)), type((1,)))        # <class 'int'> <class 'tuple'>

Point = namedtuple("Point", "x y")
p = Point(1, 2)
print(p, p.x, p[1])                 # Point(x=1, y=2) 1 2
```

---

### Q43. Split a list into chunks of size `n`. 🟢
**Explanation:** Step through the list by `n` and slice.

```python
def chunk(lst, n):
    return [lst[i:i + n] for i in range(0, len(lst), n)]

print(chunk([1, 2, 3, 4, 5, 6, 7], 3))   # [[1, 2, 3], [4, 5, 6], [7]]
```

---

### Q44. Find the missing number in `0..n`. 🟢
**Explanation:** The sum of `0..n` is `n(n+1)/2`; the difference with the actual sum is the missing value. O(n) time, O(1) space.

```python
def missing_number(nums):
    n = len(nums)
    return n * (n + 1) // 2 - sum(nums)

print(missing_number([3, 0, 1]))            # 2
print(missing_number([0, 1, 2, 4, 5, 3, 7]))  # 6
```

---

### Q45. Intersection of two lists, keeping duplicates. 🟡
**Explanation:** `Counter & Counter` keeps the minimum count of each element.

```python
from collections import Counter

a = [1, 2, 2, 3]
b = [2, 2, 2, 4]
print(list((Counter(a) & Counter(b)).elements()))   # [2, 2]
print(sorted(set(a) & set(b)))                       # [2]   (without duplicates)
```

---

### Q46. How do `zip` and `enumerate` work? 🟢
**Explanation:** `enumerate` gives `(index, item)`; `zip` pairs items from several iterables and **stops at the shortest**. Use `itertools.zip_longest` to pad.

```python
from itertools import zip_longest

names = ["a", "b", "c"]
scores = [90, 80]
for i, name in enumerate(names, start=1):
    print(i, name)                          # 1 a / 2 b / 3 c (one per line)

print(dict(zip(["a", "b"], [1, 2])))         # {'a': 1, 'b': 2}
print(list(zip(names, scores)))              # [('a', 90), ('b', 80)]
print(list(zip_longest(names, scores)))      # [('a', 90), ('b', 80), ('c', None)]
```

---
---

# 4. Dictionaries & Sets

### Q47. Show the core dictionary operations. 🟢
**Explanation:** Lookup, insert, update and delete are average O(1). Use `get` to avoid `KeyError`; `setdefault` inserts a default only if the key is missing.

```python
d = {"a": 1}
d["b"] = 2
print(d.get("z"))          # None
print(d.get("z", 0))       # 0
print(d.setdefault("c", 3))  # 3
print(d.pop("a"))          # 1
print("b" in d)            # True
print(d)                   # {'b': 2, 'c': 3}
for key, value in d.items():
    print(key, value)      # b 2 / c 3
```

---

### Q48. Merge two dictionaries. 🟢
**Explanation:** Later values win on duplicate keys. `{**a, **b}` works on all Python 3 versions; `a | b` needs 3.9+.

```python
a = {"x": 1, "y": 2}
b = {"y": 20, "z": 30}
print({**a, **b})     # {'x': 1, 'y': 20, 'z': 30}
print(a | b)          # {'x': 1, 'y': 20, 'z': 30}
merged = a.copy()
merged.update(b)
print(merged)         # {'x': 1, 'y': 20, 'z': 30}
```

---

### Q49. Invert a dictionary (keys ↔ values), including duplicate values. 🟡
**Explanation:** A simple comprehension loses entries when values repeat. Group the keys in lists instead.

```python
from collections import defaultdict

d = {"a": 1, "b": 2, "c": 1}
print({v: k for k, v in d.items()})   # {1: 'c', 2: 'b'}   <- 'a' was lost

inv = defaultdict(list)
for k, v in d.items():
    inv[v].append(k)
print(dict(inv))                      # {1: ['a', 'c'], 2: ['b']}
```

---

### Q50. Group anagrams together. 🟡
**Explanation:** Words that are anagrams share the same sorted letters, so use that as the dict key. O(n · k log k).

```python
from collections import defaultdict

def group_anagrams(words):
    groups = defaultdict(list)
    for w in words:
        groups["".join(sorted(w))].append(w)
    return list(groups.values())

print(group_anagrams(["eat", "tea", "tan", "ate", "nat", "bat"]))
# [['eat', 'tea', 'ate'], ['tan', 'nat'], ['bat']]
```

---

### Q51. Count occurrences in three different ways. 🟢
**Explanation:** `dict.get(k, 0)`, `defaultdict(int)` and `Counter` — all O(n); `Counter` is shortest and has `most_common`.

```python
from collections import Counter, defaultdict

words = "a b a c b a".split()

d1 = {}
for w in words:
    d1[w] = d1.get(w, 0) + 1

d2 = defaultdict(int)
for w in words:
    d2[w] += 1

print(d1)                  # {'a': 3, 'b': 2, 'c': 1}
print(dict(d2))            # {'a': 3, 'b': 2, 'c': 1}
print(dict(Counter(words)))  # {'a': 3, 'b': 2, 'c': 1}
```

---

### Q52. Sort a dictionary by value; find the key with the max value. 🟢
**Explanation:** Sort `items()` with a key function and rebuild the dict. `max(d, key=d.get)` returns the key with the largest value.

```python
scores = {"ann": 90, "bob": 72, "cy": 85}
print(dict(sorted(scores.items(), key=lambda kv: kv[1], reverse=True)))
# {'ann': 90, 'cy': 85, 'bob': 72}
print(max(scores, key=scores.get))   # ann
print(min(scores, key=scores.get))   # bob
```

---

### Q53. When do you use `defaultdict`? 🟢
**Explanation:** It creates a default value automatically for missing keys — ideal for grouping (`list`), counting (`int`) and unique collections (`set`) without `if key not in d` checks.

```python
from collections import defaultdict

edges = [("a", "b"), ("a", "c"), ("b", "c")]
graph = defaultdict(list)
for u, v in edges:
    graph[u].append(v)
print(dict(graph))     # {'a': ['b', 'c'], 'b': ['c']}

seen = defaultdict(set)
seen["x"].add(1)
seen["x"].add(1)
print(dict(seen))      # {'x': {1}}
```

---

### Q54. Show set operations. 🟢
**Explanation:** Sets hold unique hashable items; membership tests are O(1). Operators: `|` union, `&` intersection, `-` difference, `^` symmetric difference, `<=` subset.

```python
a = {1, 2, 3, 4}
b = {3, 4, 5}
print(sorted(a | b))    # [1, 2, 3, 4, 5]
print(sorted(a & b))    # [3, 4]
print(sorted(a - b))    # [1, 2]
print(sorted(a ^ b))    # [1, 2, 5]
print({1, 2} <= a)      # True
print(set())            # set()   ({} would create an empty dict!)
```

---

### Q55. Find the duplicates in a list. 🟢
**Explanation:** Keep a `seen` set; anything seen twice is a duplicate. Using `dict.fromkeys` removes repeated reports while keeping order. O(n).

```python
def find_duplicates(nums):
    seen, dups = set(), []
    for n in nums:
        if n in seen:
            dups.append(n)
        seen.add(n)
    return list(dict.fromkeys(dups))

print(find_duplicates([1, 2, 3, 2, 4, 3, 3]))   # [2, 3]
```

---

### Q56. Show dict and set comprehensions. 🟢
**Explanation:** Same syntax as list comprehensions but with `{k: v ...}` or `{x ...}`.

```python
print({n: n * n for n in range(1, 5)})              # {1: 1, 2: 4, 3: 9, 4: 16}
d = {"a": 3, "b": 8, "c": 10}
print({k: v for k, v in d.items() if v > 5})        # {'b': 8, 'c': 10}
print({w: len(w) for w in ["hi", "hello"]})         # {'hi': 2, 'hello': 5}
print(sorted({len(w) for w in ["a", "bb", "cc"]}))  # [1, 2]
```

---

### Q57. Return the `k` most frequent elements. 🟡
**Explanation:** `Counter.most_common(k)` does it in one line. For huge inputs `heapq.nlargest` is O(n log k).

```python
import heapq
from collections import Counter

nums = [1, 1, 1, 2, 2, 3]
k = 2
print([n for n, _ in Counter(nums).most_common(k)])        # [1, 2]

counts = Counter(nums)
print(heapq.nlargest(k, counts, key=counts.get))           # [1, 2]
```

---

### Q58. Read a value from a nested dictionary safely. 🟡
**Explanation:** Chain `get` calls with `{}` defaults, or write a small helper that walks a dotted path.

```python
data = {"user": {"profile": {"email": "a@x.com"}}}

print(data.get("user", {}).get("profile", {}).get("email"))   # a@x.com

def get_path(d, path, default=None):
    cur = d
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur

print(get_path(data, "user.profile.email"))        # a@x.com
print(get_path(data, "user.address.city", "n/a"))  # n/a
```

---

### Q59. Why must dictionary keys be hashable? Is dict order guaranteed? 🟢
**Explanation:** Dicts find keys through `hash(key)`, so keys must be immutable/hashable (`str`, `int`, `tuple` of hashables). Lists and dicts are not hashable. Since Python 3.7, dicts preserve **insertion order**.

```python
d = {(1, 2): "tuple key works"}
print(d[(1, 2)])        # tuple key works

try:
    d[[1, 2]] = "x"
except TypeError as e:
    print(e)            # unhashable type: 'list'

print(list({"b": 1, "a": 2}))   # ['b', 'a']  (insertion order)
```

---

### Q60. Count subarrays whose sum equals `k` (prefix sums + dict). 🟡
**Explanation:** If the running sum is `p` and we have seen `p - k` before, the elements in between sum to `k`. Store how many times each prefix sum occurred. O(n).

```python
def subarray_sum(nums, k):
    count = prefix = 0
    seen = {0: 1}
    for n in nums:
        prefix += n
        count += seen.get(prefix - k, 0)
        seen[prefix] = seen.get(prefix, 0) + 1
    return count

print(subarray_sum([1, 1, 1], 2))   # 2
print(subarray_sum([1, 2, 3], 3))   # 2
```

---

### Q61. Longest consecutive sequence in an unsorted list in O(n). 🟡
**Explanation:** Put numbers in a set. Only start counting from a number whose predecessor `n-1` is **not** in the set; then walk upward.

```python
def longest_consecutive(nums):
    s = set(nums)
    best = 0
    for n in s:
        if n - 1 not in s:
            m = n
            while m + 1 in s:
                m += 1
            best = max(best, m - n + 1)
    return best

print(longest_consecutive([100, 4, 200, 1, 3, 2]))   # 4
```

---

### Q62. Word frequency sorted by count (desc) then alphabetically. 🟡
**Explanation:** Sort with a tuple key; negate the count for descending order.

```python
from collections import Counter

words = "b a c a b a".split()
counts = Counter(words)
print(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
# [('a', 3), ('b', 2), ('c', 1)]
```

---

# 5. Control Flow, Functions & Recursion

### Q63. FizzBuzz. 🟢
**Explanation:** Test the combined case (multiple of 15) **first**, otherwise it is never reached.

```python
def fizzbuzz(n):
    out = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            out.append("FizzBuzz")
        elif i % 3 == 0:
            out.append("Fizz")
        elif i % 5 == 0:
            out.append("Buzz")
        else:
            out.append(str(i))
    return out

print(fizzbuzz(15))
# ['1', '2', 'Fizz', '4', 'Buzz', 'Fizz', '7', '8', 'Fizz', 'Buzz', '11', 'Fizz', '13', '14', 'FizzBuzz']
```

---

### Q64. Check if a number is prime; list all primes up to `n`. 🟢
**Explanation:** Only test divisors up to `√n`. For many primes use the **Sieve of Eratosthenes** (O(n log log n)).

```python
import math

def is_prime(n):
    if n < 2:
        return False
    for i in range(2, math.isqrt(n) + 1):
        if n % i == 0:
            return False
    return True

def sieve(n):
    flags = [True] * (n + 1)
    flags[0:2] = [False, False]
    for i in range(2, math.isqrt(n) + 1):
        if flags[i]:
            for j in range(i * i, n + 1, i):
                flags[j] = False
    return [i for i, ok in enumerate(flags) if ok]

print(is_prime(29), is_prime(30))   # True False
print(sieve(30))                    # [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
```

---

### Q65. Fibonacci: iterative and memoized recursion. 🟢
**Explanation:** Naive recursion is O(2ⁿ). Iteration is O(n) time / O(1) space; `lru_cache` makes the recursion O(n).

```python
from functools import lru_cache

def fib_iter(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

@lru_cache(maxsize=None)
def fib_memo(n):
    return n if n < 2 else fib_memo(n - 1) + fib_memo(n - 2)

print([fib_iter(i) for i in range(10)])   # [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
print(fib_memo(50))                        # 12586269025
```

---

### Q66. Factorial: recursive vs iterative. What is the recursion limit? 🟢
**Explanation:** Every recursive call uses a stack frame; Python's default limit is about 1000 (`sys.getrecursionlimit()`), so very deep recursion raises `RecursionError`. Prefer loops for deep iteration.

```python
import math

def fact_rec(n):
    return 1 if n <= 1 else n * fact_rec(n - 1)

def fact_iter(n):
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result

print(fact_rec(5), fact_iter(5), math.factorial(5))   # 120 120 120
```

---

### Q67. Compute GCD and LCM. 🟢
**Explanation:** Euclid's algorithm: `gcd(a, b) = gcd(b, a % b)`. Then `lcm = a * b // gcd`.

```python
import math

def gcd(a, b):
    while b:
        a, b = b, a % b
    return a

def lcm(a, b):
    return a * b // gcd(a, b)

print(gcd(48, 18), lcm(48, 18))      # 6 144
print(math.gcd(48, 18))               # 6
```

---

### Q68. Digit problems: sum of digits, reverse an integer, palindrome number. 🟢
**Explanation:** Either convert to string, or use `% 10` and `// 10` to peel digits.

```python
def digit_sum(n):
    total = 0
    n = abs(n)
    while n:
        n, d = divmod(n, 10)
        total += d
    return total

def reverse_int(n):
    sign = -1 if n < 0 else 1
    return sign * int(str(abs(n))[::-1])

def is_palindrome_number(n):
    return n >= 0 and str(n) == str(n)[::-1]

print(digit_sum(12345))          # 15
print(reverse_int(-123))         # -321
print(is_palindrome_number(121)) # True
```

---

### Q69. Convert between decimal and binary / hex. 🟢
**Explanation:** Built-ins: `bin`, `hex`, `int(s, base)`, and format spec `b`. Manually: repeatedly divide by 2 and collect remainders.

```python
def to_binary(n):
    if n == 0:
        return "0"
    bits = []
    while n:
        bits.append(str(n % 2))
        n //= 2
    return "".join(reversed(bits))

print(bin(10))              # 0b1010
print(to_binary(10))        # 1010
print(int("1010", 2))       # 10
print(hex(255))             # 0xff
print(f"{10:08b}")          # 00001010
```

---

### Q70. Explain `lambda`, `map`, `filter`, `reduce`. 🟢
**Explanation:** `lambda` is a small anonymous function. `map` transforms, `filter` selects, `reduce` folds a sequence into one value. Comprehensions are usually more readable.

```python
from functools import reduce

nums = [1, 2, 3, 4, 5]
print(list(map(lambda x: x * 2, nums)))        # [2, 4, 6, 8, 10]
print(list(filter(lambda x: x % 2, nums)))     # [1, 3, 5]
print(reduce(lambda a, b: a * b, nums))        # 120
print([x * 2 for x in nums])                   # [2, 4, 6, 8, 10]
```

---

### Q71. What is a closure? 🟡
**Explanation:** An inner function that remembers variables from the enclosing function after that function has returned. Useful for factories and simple state.

```python
def make_multiplier(factor):
    def multiply(x):
        return x * factor
    return multiply

def make_counter():
    count = 0
    def counter():
        nonlocal count
        count += 1
        return count
    return counter

triple = make_multiplier(3)
print(triple(5))        # 15

c = make_counter()
print(c(), c(), c())    # 1 2 3
```

---

### Q72. Generate all subsets and all permutations. 🟡
**Explanation:** Subsets: for each new element, add it to every existing subset (2ⁿ results). Permutations: pick each element as the first one, permute the rest (n! results).

```python
from itertools import permutations

def subsets(nums):
    result = [[]]
    for n in nums:
        result += [r + [n] for r in result]
    return result

def perms(s):
    if len(s) <= 1:
        return [s]
    out = []
    for i, ch in enumerate(s):
        for p in perms(s[:i] + s[i + 1:]):
            out.append(ch + p)
    return out

print(subsets([1, 2, 3]))
# [[], [1], [2], [1, 2], [3], [1, 3], [2, 3], [1, 2, 3]]
print(perms("abc"))                       # ['abc', 'acb', 'bac', 'bca', 'cab', 'cba']
print(len(list(permutations([1, 2, 3]))))  # 6
```

---

### Q73. Does Python pass arguments by value or by reference? 🟡
**Explanation:** Neither exactly — it passes **object references by value** ("pass by assignment"). Mutating the object inside a function is visible outside; rebinding the parameter name is not.

```python
def append_item(lst):
    lst.append(1)        # mutates the caller's list

def rebind(lst):
    lst = [99]           # only rebinds the local name

a = []
append_item(a)
print(a)                 # [1]
rebind(a)
print(a)                 # [1]
```

---

### Q74. What does `else` do on a `for` / `while` loop? 🟡
**Explanation:** The `else` block runs only if the loop finished **without** hitting `break`. Handy for "search and not found" logic.

```python
for n in [2, 4, 6]:
    if n % 2:
        print("found odd")
        break
else:
    print("no odd numbers")   # no odd numbers
```

---

### Q75. Show the ternary operator and the walrus operator. 🟢
**Explanation:** `a if cond else b` is an expression. The walrus `:=` (3.8+) assigns a value inside an expression, avoiding a second computation.

```python
age = 20
status = "adult" if age >= 18 else "minor"
print(status)                        # adult

data = [1, 2, 3]
if (n := len(data)) > 2:
    print(f"{n} items")              # 3 items
```

---

### Q76. What are positional-only (`/`) and keyword-only (`*`) parameters? 🟡
**Explanation:** Parameters before `/` must be passed by position; parameters after `*` must be passed by keyword. This makes APIs clearer and safer.

```python
def f(a, b, /, c, *, d):
    return a, b, c, d

print(f(1, 2, 3, d=4))       # (1, 2, 3, 4)
print(f(1, 2, c=3, d=4))     # (1, 2, 3, 4)
try:
    f(1, 2, 3, 4)            # d must be a keyword
except TypeError:
    print("TypeError")       # TypeError
```

---
---

# 6. Object-Oriented Programming

### Q77. Write a class with `__init__`, `__str__` and `__repr__`. 🟢
**Explanation:** `__str__` is the friendly text for users (`print`), `__repr__` is the unambiguous developer text (shown in the REPL and in containers).

```python
class Book:
    def __init__(self, title, pages):
        self.title = title
        self.pages = pages

    def __str__(self):
        return f"{self.title} ({self.pages} pages)"

    def __repr__(self):
        return f"Book(title={self.title!r}, pages={self.pages})"

b = Book("Dune", 412)
print(b)          # Dune (412 pages)
print(repr(b))    # Book(title='Dune', pages=412)
print([b])        # [Book(title='Dune', pages=412)]
```

---

### Q78. Class attributes vs instance attributes. 🟢
**Explanation:** Class attributes are shared by all instances; instance attributes belong to one object. Assigning through an instance creates a new instance attribute that *shadows* the class attribute.

```python
class Employee:
    company = "Acme"        # class attribute
    total = 0

    def __init__(self, name):
        self.name = name    # instance attribute
        Employee.total += 1

e1, e2 = Employee("Ann"), Employee("Bob")
print(Employee.total)       # 2
e1.company = "Other"        # shadows the class attribute for e1 only
print(e1.company, e2.company, Employee.company)   # Other Acme Acme
```

---

### Q79. Explain `@classmethod`, `@staticmethod` and `@property`. 🟡
**Explanation:** An instance method receives `self`; a classmethod receives the class (`cls`) — often used as an alternative constructor; a staticmethod receives neither and is just a function grouped in the class; a property exposes a method as an attribute (with validation in the setter).

```python
class Temp:
    def __init__(self, celsius):
        self.celsius = celsius          # goes through the setter

    @property
    def celsius(self):
        return self._c

    @celsius.setter
    def celsius(self, value):
        if value < -273.15:
            raise ValueError("below absolute zero")
        self._c = value

    @property
    def fahrenheit(self):
        return self._c * 9 / 5 + 32

    @classmethod
    def from_fahrenheit(cls, f):
        return cls((f - 32) * 5 / 9)

    @staticmethod
    def is_freezing(c):
        return c <= 0

print(Temp(100).fahrenheit)             # 212.0
print(Temp.from_fahrenheit(32).celsius) # 0.0
print(Temp.is_freezing(-5))             # True
try:
    Temp(-300)
except ValueError as e:
    print(e)                            # below absolute zero
```

---

### Q80. Inheritance, `super()` and method overriding (polymorphism). 🟢
**Explanation:** A subclass reuses the parent's code and overrides what differs. `super()` calls the parent version. Code that works with the parent type works with any child.

```python
class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        return f"{self.name} makes a sound"

class Dog(Animal):
    def speak(self):
        return f"{self.name} says Woof"

class Cat(Animal):
    def __init__(self, name, indoor=True):
        super().__init__(name)
        self.indoor = indoor

    def speak(self):
        return f"{self.name} says Meow"

for pet in [Dog("Rex"), Cat("Tom"), Animal("Generic")]:
    print(pet.speak())
# Rex says Woof
# Tom says Meow
# Generic makes a sound
```

---

### Q81. Implement operator overloading with dunder methods. 🟡
**Explanation:** Special methods let your objects work with Python syntax: `+` → `__add__`, `==` → `__eq__`, `abs()` → `__abs__`, `len()` → `__len__`. Return `NotImplemented` for unsupported operand types.

```python
class Vector:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __add__(self, other):
        if not isinstance(other, Vector):
            return NotImplemented
        return Vector(self.x + other.x, self.y + other.y)

    def __mul__(self, k):
        return Vector(self.x * k, self.y * k)

    def __eq__(self, other):
        return isinstance(other, Vector) and (self.x, self.y) == (other.x, other.y)

    def __abs__(self):
        return (self.x ** 2 + self.y ** 2) ** 0.5

    def __repr__(self):
        return f"Vector({self.x}, {self.y})"

v = Vector(1, 2) + Vector(3, 4)
print(v)                              # Vector(4, 6)
print(v * 2)                          # Vector(8, 12)
print(v == Vector(4, 6))              # True
print(abs(Vector(3, 4)))              # 5.0
```

---

### Q82. What is an abstract base class (ABC)? 🟡
**Explanation:** An ABC defines a contract: subclasses **must** implement the abstract methods, and you cannot instantiate the ABC itself.

```python
from abc import ABC, abstractmethod
import math

class Shape(ABC):
    @abstractmethod
    def area(self):
        ...

class Circle(Shape):
    def __init__(self, r):
        self.r = r
    def area(self):
        return math.pi * self.r ** 2

class Rect(Shape):
    def __init__(self, w, h):
        self.w, self.h = w, h
    def area(self):
        return self.w * self.h

print(round(Circle(1).area(), 2))   # 3.14
print(Rect(2, 3).area())            # 6
try:
    Shape()
except TypeError:
    print("cannot instantiate abstract class")   # cannot instantiate abstract class
```

---

### Q83. What is a `dataclass` and why use it? 🟡
**Explanation:** `@dataclass` auto-generates `__init__`, `__repr__` and `__eq__` from annotated fields. Use `field(default_factory=list)` for mutable defaults, `frozen=True` for immutability, `order=True` for sorting.

```python
from dataclasses import dataclass, field

@dataclass(order=True)
class Item:
    name: str
    price: float
    qty: int = 1
    tags: list = field(default_factory=list)

a = Item("pen", 1.5)
print(a)                                  # Item(name='pen', price=1.5, qty=1, tags=[])
print(a == Item("pen", 1.5))              # True
print(sorted([Item("b", 2), Item("a", 9)])[0].name)   # a
```

---

### Q84. Encapsulation: `_protected`, `__private` and name mangling. 🟡
**Explanation:** Python relies on conventions. `_x` means "internal, please don't touch". `__x` is renamed to `_ClassName__x` (name mangling) to avoid accidental overrides — it is not true security.

```python
class Account:
    def __init__(self, balance):
        self.__balance = balance

    def deposit(self, amount):
        if amount <= 0:
            raise ValueError("amount must be positive")
        self.__balance += amount

    @property
    def balance(self):
        return self.__balance

acct = Account(100)
acct.deposit(50)
print(acct.balance)                 # 150
print(hasattr(acct, "__balance"))   # False
print(acct._Account__balance)       # 150
```

---

### Q85. Composition vs inheritance — when do you prefer composition? 🟡
**Explanation:** Inheritance models "is-a"; composition models "has-a". Prefer composition when you just want to reuse behaviour — it is more flexible and easier to test (swap the part).

```python
class Engine:
    def start(self):
        return "engine started"

class Car:
    def __init__(self, engine):
        self.engine = engine       # Car HAS an Engine

    def start(self):
        return f"car: {self.engine.start()}"

print(Car(Engine()).start())       # car: engine started
```

---

### Q86. Implement a Stack and a Queue. 🟢
**Explanation:** Stack = LIFO (list `append`/`pop` are O(1)). Queue = FIFO — use `collections.deque` (`list.pop(0)` is O(n)).

```python
from collections import deque

class Stack:
    def __init__(self):
        self._items = []
    def push(self, x):
        self._items.append(x)
    def pop(self):
        return self._items.pop()
    def peek(self):
        return self._items[-1]
    def __len__(self):
        return len(self._items)

class Queue:
    def __init__(self):
        self._items = deque()
    def enqueue(self, x):
        self._items.append(x)
    def dequeue(self):
        return self._items.popleft()
    def __len__(self):
        return len(self._items)

s = Stack(); s.push(1); s.push(2)
print(s.pop(), s.peek(), len(s))    # 2 1 1
q = Queue(); q.enqueue("a"); q.enqueue("b")
print(q.dequeue(), len(q))          # a 1
```

---

### Q87. What is the MRO (method resolution order) in multiple inheritance? 🟡
**Explanation:** Python uses C3 linearization to decide which parent is searched first. `super()` follows the MRO, so each class in a diamond is called once.

```python
class A:
    def hello(self): return "A"
class B(A):
    def hello(self): return "B>" + super().hello()
class C(A):
    def hello(self): return "C>" + super().hello()
class D(B, C):
    def hello(self): return "D>" + super().hello()

print([c.__name__ for c in D.__mro__])   # ['D', 'B', 'C', 'A', 'object']
print(D().hello())                        # D>B>C>A
```

---
---

# 7. Iterators, Generators, Decorators & Context Managers

### Q88. Explain the iterator protocol and build a custom iterator. 🟡
**Explanation:** An *iterable* has `__iter__()`; an *iterator* has `__next__()` and raises `StopIteration` when finished. A `for` loop calls `iter()` once and `next()` repeatedly.

```python
class CountDown:
    def __init__(self, start):
        self.current = start

    def __iter__(self):
        return self

    def __next__(self):
        if self.current <= 0:
            raise StopIteration
        value = self.current
        self.current -= 1
        return value

print(list(CountDown(3)))     # [3, 2, 1]

it = iter([10, 20])
print(next(it), next(it))     # 10 20
print(next(it, "done"))       # done
```

---

### Q89. What is a generator and why use `yield`? 🟡
**Explanation:** A function with `yield` returns a generator that produces values **lazily**, one at a time, keeping its local state between calls. It uses O(1) memory — ideal for large files or infinite streams.

```python
def squares(n):
    for i in range(n):
        yield i * i

g = squares(4)
print(next(g), next(g))    # 0 1
print(list(g))              # [4, 9]   (continues where it stopped)
print(list(g))              # []       (a generator is exhausted after one pass)
```

---

### Q90. Generator expression vs list comprehension? 🟢
**Explanation:** `[...]` builds the whole list in memory; `(...)` is lazy and creates values on demand. Use a generator expression when you only iterate once (e.g. inside `sum`, `any`, `max`).

```python
total = sum(x for x in range(1, 101))
print(total)                          # 5050

gen = (x * x for x in range(3))
print(type(gen).__name__)             # generator
print(any(n > 100 for n in [1, 5, 500]))   # True (stops at first match)
```

---

### Q91. Write a decorator that logs function calls. Why `functools.wraps`? 🟡
**Explanation:** A decorator takes a function and returns a wrapped version. `@wraps(func)` copies the original name and docstring so debugging and introspection still work.

```python
from functools import wraps

def log_calls(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"calling {func.__name__}{args}")
        result = func(*args, **kwargs)
        print(f"-> {result}")
        return result
    return wrapper

@log_calls
def add(a, b):
    """Add two numbers."""
    return a + b

add(2, 3)
# calling add(2, 3)
# -> 5
print(add.__name__)    # add
```

---

### Q92. Write a decorator that takes arguments (a `retry` decorator). 🟡
**Explanation:** A decorator with arguments is a *function that returns a decorator*: three nested levels (arguments → function → wrapper).

```python
from functools import wraps

def retry(times):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == times:
                        raise
        return wrapper
    return decorator

calls = {"n": 0}

@retry(3)
def flaky():
    calls["n"] += 1
    if calls["n"] < 3:
        raise ConnectionError("down")
    return "ok"

print(flaky(), calls["n"])    # ok 3
```

---

### Q93. What is a context manager? Write one two ways. 🟡
**Explanation:** The `with` statement guarantees cleanup. Implement `__enter__` / `__exit__`, or use the `@contextmanager` decorator with a `yield` (code after `yield` is the cleanup).

```python
from contextlib import contextmanager

class Managed:
    def __enter__(self):
        print("open")
        return self
    def __exit__(self, exc_type, exc, tb):
        print("close")
        return False          # do not swallow exceptions

with Managed():
    print("working")
# open / working / close

@contextmanager
def opened(name):
    print(f"open {name}")
    try:
        yield name
    finally:
        print(f"close {name}")

with opened("db") as db:
    print("using", db)
# open db / using db / close db
```

---

### Q94. Show the most useful `itertools` functions. 🟡
**Explanation:** `itertools` provides fast, memory-efficient building blocks for loops.

```python
from itertools import chain, islice, count, product, combinations, accumulate, groupby

print(list(chain([1, 2], [3])))                     # [1, 2, 3]
print(list(islice(count(10), 3)))                    # [10, 11, 12]
print(list(product("ab", [1, 2])))                   # [('a', 1), ('a', 2), ('b', 1), ('b', 2)]
print(list(combinations([1, 2, 3], 2)))              # [(1, 2), (1, 3), (2, 3)]
print(list(accumulate([1, 2, 3, 4])))                # [1, 3, 6, 10]

words = sorted(["apple", "avocado", "banana", "blueberry", "cherry"])
print({k: list(g) for k, g in groupby(words, key=lambda w: w[0])})
# {'a': ['apple', 'avocado'], 'b': ['banana', 'blueberry'], 'c': ['cherry']}
```

---

### Q95. Write an infinite generator and use `yield from`. 🟡
**Explanation:** Infinite generators are safe because values are produced lazily; take a slice with `islice`. `yield from` delegates to another iterable.

```python
from itertools import islice

def fib_gen():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

print(list(islice(fib_gen(), 10)))    # [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]

def flatten(nested):
    for item in nested:
        if isinstance(item, list):
            yield from flatten(item)
        else:
            yield item

print(list(flatten([1, [2, [3, 4]], 5])))   # [1, 2, 3, 4, 5]
```

---

### Q96. What do `functools.lru_cache` and `functools.partial` do? 🟡
**Explanation:** `lru_cache` memoizes results (arguments must be hashable). `partial` pre-fills some arguments of a function to create a new, simpler one.

```python
from functools import lru_cache, partial

@lru_cache(maxsize=None)
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)

print(fib(30))                 # 832040
print(fib.cache_info())        # CacheInfo(hits=28, misses=31, maxsize=None, currsize=31)

binary_to_int = partial(int, base=2)
print(binary_to_int("101"))    # 5
```

---

### Q97. Write your own memoization decorator. 🟡
**Explanation:** Store results in a dict keyed by the arguments; return the stored value when the same arguments appear again.

```python
from functools import wraps

def memoize(func):
    cache = {}
    @wraps(func)
    def wrapper(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    wrapper.cache = cache
    return wrapper

@memoize
def slow_square(n):
    print(f"computing {n}")
    return n * n

print(slow_square(4))    # computing 4  then 16
print(slow_square(4))    # 16  (cached, no "computing" line)
```

---
---

# 8. Exceptions & File Handling

### Q98. Explain `try / except / else / finally`. 🟢
**Explanation:** `except` handles errors, `else` runs only if **no** exception happened, `finally` **always** runs (cleanup). Catch specific exceptions, never a bare `except:`.

```python
def divide(a, b):
    try:
        result = a / b
    except ZeroDivisionError:
        print("cannot divide by zero")
        return None
    else:
        print("ok")
        return result
    finally:
        print("done")

print(divide(4, 2))   # ok / done / 2.0
print(divide(4, 0))   # cannot divide by zero / done / None
```

---

### Q99. Create and raise a custom exception. 🟢
**Explanation:** Subclass `Exception`. Carry useful data on the exception and give it a clear message.

```python
class InsufficientFunds(Exception):
    def __init__(self, balance, amount):
        super().__init__(f"need {amount}, have {balance}")
        self.balance = balance
        self.amount = amount

def withdraw(balance, amount):
    if amount > balance:
        raise InsufficientFunds(balance, amount)
    return balance - amount

try:
    withdraw(20, 50)
except InsufficientFunds as e:
    print(e)               # need 50, have 20
    print(e.amount - e.balance)   # 30
```

---

### Q100. Re-raise an exception and chain exceptions with `raise ... from`. 🟡
**Explanation:** A bare `raise` re-raises the current exception (after logging, for example). `raise New from old` records the original error in `__cause__` so the root cause is not lost.

```python
def load_config(text):
    try:
        return int(text)
    except ValueError as e:
        raise RuntimeError("bad config") from e

try:
    load_config("x")
except RuntimeError as e:
    print(e)                          # bad config
    print(type(e.__cause__).__name__) # ValueError

try:
    try:
        1 / 0
    except ZeroDivisionError:
        print("logging the error")    # logging the error
        raise                         # re-raise unchanged
except ZeroDivisionError:
    print("caught again")             # caught again
```

---

### Q101. Read and write a text file safely. 🟢
**Explanation:** Always use `with open(...)` so the file is closed even on errors. Iterating the file object reads **line by line** without loading everything into memory. Modes: `r` read, `w` overwrite, `a` append.

```python
import os, tempfile

path = os.path.join(tempfile.gettempdir(), "demo_karat.txt")

with open(path, "w", encoding="utf-8") as f:
    f.write("line one\nline two\n\nline four\n")

with open(path, encoding="utf-8") as f:
    lines = [ln.rstrip("\n") for ln in f]
print(lines)                              # ['line one', 'line two', '', 'line four']
print(sum(1 for ln in lines if ln))       # 3   (non-empty lines)

with open(path, "a", encoding="utf-8") as f:
    f.write("appended\n")
with open(path, encoding="utf-8") as f:
    print(f.read().count("\n"))           # 5

os.remove(path)
```

---

### Q102. Work with JSON (`dumps`, `loads`, `dump`, `load`). 🟢
**Explanation:** `dumps`/`loads` work with strings; `dump`/`load` work with file objects. Python `None/True` ↔ JSON `null/true`; tuples become arrays.

```python
import json

data = {"a": [1, 2], "b": None, "c": True}
text = json.dumps(data)
print(text)                               # {"a": [1, 2], "b": null, "c": true}
print(json.loads('{"x": 1.5}'))           # {'x': 1.5}
print(json.loads(text) == data)           # True
print(json.dumps({"b": 1, "a": 2}, indent=2, sort_keys=True))
# {
#   "a": 2,
#   "b": 1
# }
```

---

### Q103. Read CSV data and total a column per group. 🟡
**Explanation:** `csv.DictReader` yields each row as a dict keyed by the header. Convert numbers explicitly (all fields are strings).

```python
import csv, io
from collections import defaultdict

raw = "name,dept,salary\nann,eng,100\nbob,eng,80\ncy,ops,70\n"
totals = defaultdict(int)
for row in csv.DictReader(io.StringIO(raw)):
    totals[row["dept"]] += int(row["salary"])

print(dict(totals))    # {'eng': 180, 'ops': 70}
```

---

### Q104. Parse log lines: count by level and list the errors. 🟡
**Explanation:** Typical Karat warm-up. Split each line into fixed fields with `split(maxsplit)` so the message (which contains spaces) stays in one piece. Always handle malformed lines.

```python
from collections import Counter

logs = [
    "2024-05-01 10:00:01 INFO user login",
    "2024-05-01 10:00:05 ERROR payment timeout",
    "2024-05-01 10:01:10 WARN slow response",
    "2024-05-01 10:02:00 ERROR db down",
    "2024-05-01 10:03:00 INFO user logout",
    "garbage",
]

counts = Counter()
errors = []
for line in logs:
    parts = line.split(" ", 3)
    if len(parts) < 4:
        continue                       # skip malformed lines
    date, time, level, message = parts
    counts[level] += 1
    if level == "ERROR":
        errors.append((time, message))

print(dict(counts))   # {'INFO': 2, 'ERROR': 2, 'WARN': 1}
print(errors)         # [('10:00:05', 'payment timeout'), ('10:02:00', 'db down')]
```

---

### Q105. Use `pathlib` for file paths. 🟢
**Explanation:** `pathlib.Path` is the modern, OS-independent way to handle paths: `/` joins, and properties give name/suffix/parent. (`PurePosixPath` is used here so the output is the same on every OS.)

```python
from pathlib import PurePosixPath, Path

p = PurePosixPath("/data/logs/app.log")
print(p.name)          # app.log
print(p.stem)          # app
print(p.suffix)        # .log
print(p.parent)        # /data/logs
print(p.parent / "other.txt")   # /data/logs/other.txt

# With a real filesystem you would use Path(...).exists(), .read_text(), .write_text(),
# .glob("*.log"), .mkdir(parents=True, exist_ok=True)
print(Path("x.txt").suffix)     # .txt
```

---

# 9. Standard Library & Python Knowledge

### Q106. What are `deque`, `Counter` and `OrderedDict` / `ChainMap` good for? 🟡
**Explanation:** `deque` gives O(1) appends/pops at **both** ends and an optional `maxlen` (sliding window). `Counter` supports arithmetic between counts. Plain dicts already keep insertion order, so `OrderedDict` is only needed for `move_to_end` / order-sensitive equality.

```python
from collections import deque, Counter

d = deque([1, 2, 3], maxlen=3)
d.append(4)
print(d)                  # deque([2, 3, 4], maxlen=3)
d.appendleft(0)
print(d)                  # deque([0, 2, 3], maxlen=3)
d.rotate(1)
print(list(d))            # [3, 0, 2]

print(dict(Counter("aab") + Counter("bc")))   # {'a': 2, 'b': 2, 'c': 1}
```

---

### Q107. How do you use `heapq` (min-heap, max-heap, priority queue, k-th largest)? 🟡
**Explanation:** `heapq` is a **min-heap** on a list: push/pop are O(log n), peek is `h[0]`. For a max-heap, push negated values. Tuples `(priority, item)` give a priority queue.

```python
import heapq

h = []
for x in [5, 1, 8, 3]:
    heapq.heappush(h, x)
print(h[0])                                        # 1  (smallest)
print([heapq.heappop(h) for _ in range(len(h))])   # [1, 3, 5, 8]

nums = [4, 9, 1, 7, 3]
print(heapq.nlargest(2, nums))                     # [9, 7]
print(heapq.nlargest(2, nums)[-1])                 # 7   (2nd largest)

pq = []
heapq.heappush(pq, (2, "write tests"))
heapq.heappush(pq, (1, "fix prod bug"))
print(heapq.heappop(pq))                           # (1, 'fix prod bug')

maxheap = [-x for x in nums]
heapq.heapify(maxheap)
print(-heapq.heappop(maxheap))                     # 9
```

---

### Q108. What is `bisect` used for? 🟡
**Explanation:** Binary search on a **sorted** list in O(log n): find insertion points or keep a list sorted with `insort`.

```python
import bisect

a = [1, 3, 5, 7]
print(bisect.bisect_left(a, 5))    # 2
print(bisect.bisect_right(a, 5))   # 3
print(bisect.bisect_left(a, 4))    # 2
bisect.insort(a, 4)
print(a)                           # [1, 3, 4, 5, 7]
```

---

### Q109. Use regular expressions: find, groups, substitute, split. 🟡
**Explanation:** `findall` returns all matches; `match` anchors at the start; `search` scans; `(...)` captures groups; `(?P<name>...)` names them; `sub` replaces; use raw strings `r"..."`.

```python
import re

text = "Contact: ann@x.com, bob.smith@mail.org"
print(re.findall(r"[\w.]+@[\w.]+\.\w+", text))
# ['ann@x.com', 'bob.smith@mail.org']

m = re.match(r"(\d{4})-(\d{2})-(\d{2})", "2024-05-01 rest")
print(m.groups())                                     # ('2024', '05', '01')

m = re.search(r"(?P<user>\w+)@(?P<host>[\w.]+)", "ann@x.com")
print(m.groupdict())                                  # {'user': 'ann', 'host': 'x.com'}

print(re.sub(r"\d+", "#", "a1b22"))                   # a#b#
print(re.split(r"[,;]\s*", "a, b;c"))                 # ['a', 'b', 'c']
```

---

### Q110. Work with dates and times (`datetime`). 🟡
**Explanation:** `strptime` parses text → datetime, `strftime` formats datetime → text. Subtracting datetimes gives a `timedelta`; `timedelta` can be added to a datetime.

```python
from datetime import datetime, timedelta

t1 = datetime.strptime("2024-05-01 10:00:00", "%Y-%m-%d %H:%M:%S")
t2 = datetime(2024, 5, 1, 10, 45, 30)

print(t2 - t1)                        # 0:45:30
print((t2 - t1).total_seconds())      # 2730.0
print(t1 + timedelta(days=30))        # 2024-05-31 10:00:00
print(t1.strftime("%d %b %Y"))        # 01 May 2024
print(t1.weekday())                   # 2   (Monday=0, so 2 = Wednesday)
print(datetime.fromisoformat("2024-05-01").date())   # 2024-05-01
```

---

### Q111. How do you read command-line arguments and environment variables? 🟢
**Explanation:** `sys.argv` is the raw list; `argparse` gives typed options, defaults and `--help`. `os.environ.get(name, default)` reads environment variables (never hard-code secrets).

```python
import argparse, os

parser = argparse.ArgumentParser(description="demo")
parser.add_argument("--n", type=int, default=1)
parser.add_argument("--verbose", action="store_true")

args = parser.parse_args(["--n", "3", "--verbose"])   # normally: parser.parse_args()
print(args.n, args.verbose)                            # 3 True
print(os.environ.get("MISSING_VAR", "default"))        # default
```

---

### Q112. Handy `math`, `statistics` and `random` functions. 🟢
**Explanation:** Know `ceil`/`floor`, `sqrt`, `isqrt`, `mean`/`median`/`mode`, `random.choice/sample/shuffle`, and `random.seed` for reproducible tests.

```python
import math, statistics, random

print(math.sqrt(16), math.ceil(2.1), math.floor(-2.1))   # 4.0 3 -3
print(math.isqrt(17))                                    # 4
print(statistics.mean([1, 2, 3, 4]))                     # 2.5
print(statistics.median([1, 3, 2]))                      # 2
print(statistics.mode([1, 1, 2]))                        # 1

random.seed(0)
print(len(random.sample(range(10), 3)))                  # 3
```

---

### Q113. What are the time complexities of common Python operations? 🟡
**Explanation:** Knowing this decides which data structure to use. Membership in a list is O(n) but in a set/dict it is O(1) on average. `list.insert(0, x)` / `pop(0)` are O(n); use `deque`. String concatenation in a loop is O(n²) — build a list and `"".join`.

| Operation | list | dict / set | deque |
|---|---|---|---|
| index / lookup | O(1) | O(1) avg | O(n) middle |
| append / add | O(1) | O(1) avg | O(1) |
| insert/pop at front | O(n) | – | O(1) |
| `x in c` | O(n) | O(1) avg | O(n) |
| sort | O(n log n) | – | – |

```python
big_list = list(range(100_000))
big_set = set(big_list)
print(99_999 in big_list)   # True   (scans up to 100,000 items)
print(99_999 in big_set)    # True   (one hash lookup)

parts = [str(i) for i in range(5)]
print("".join(parts))        # 01234  (fast way to build strings)
```

---

### Q114. What is the GIL? Threads vs processes vs asyncio? 🟡
**Explanation:** The Global Interpreter Lock lets only one thread run Python bytecode at a time. So: **threads** help for I/O-bound work (network, disk); **processes** (`multiprocessing`, `ProcessPoolExecutor`) are needed for CPU-bound work; **asyncio** handles many concurrent I/O tasks on one thread.

```python
from concurrent.futures import ThreadPoolExecutor
import time

def fake_io(x):
    time.sleep(0.01)       # pretend to wait for a network call
    return x * 2

with ThreadPoolExecutor(max_workers=3) as ex:
    print(list(ex.map(fake_io, [1, 2, 3])))    # [2, 4, 6]  (order is preserved)

# CPU-bound: use ProcessPoolExecutor (guard with `if __name__ == "__main__":`)
```

---

### Q115. `sort()` vs `sorted()`, stability, and sorting by several keys. 🟡
**Explanation:** `list.sort()` sorts in place and returns `None`; `sorted()` returns a new list from any iterable. Both are stable (Timsort, O(n log n)). You cannot compare unrelated types in Python 3.

```python
words = ["pear", "fig", "apple", "kiwi"]
print(sorted(words, key=lambda w: (len(w), w)))   # ['fig', 'kiwi', 'pear', 'apple']
print(words.sort())                                # None
print(words)                                       # ['apple', 'fig', 'kiwi', 'pear']

try:
    sorted([3, "a"])
except TypeError:
    print("cannot compare int and str")            # cannot compare int and str
```

---
---

# 10. Karat-Style Algorithm & Data-Processing Problems

> These mirror the style of the real interview: read a small data set, build the right data structure, handle edge cases, then answer follow-up questions.

### Q116. Valid parentheses. 🟢
**Explanation:** Use a stack. Push opening brackets; on a closing bracket the top of the stack must be its partner. At the end the stack must be empty. O(n).

```python
def is_valid(s):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack

for t in ["()[]{}", "(]", "([)]", "{[]}", "(("]:
    print(t, is_valid(t))
# ()[]{} True / (] False / ([)] False / {[]} True / (( False
```

---

### Q117. Binary search. 🟢
**Explanation:** Repeatedly halve the search range of a sorted list. O(log n). Watch the loop condition (`lo <= hi`) and avoid infinite loops.

```python
def binary_search(a, target):
    lo, hi = 0, len(a) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if a[mid] == target:
            return mid
        if a[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1

a = [1, 3, 5, 7, 9]
print(binary_search(a, 7))   # 3
print(binary_search(a, 4))   # -1
```

---

### Q118. Merge overlapping intervals. 🟡
**Explanation:** Sort by start. Extend the last merged interval if the next one starts before it ends; otherwise start a new one. O(n log n).

```python
def merge_intervals(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged

print(merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]))   # [[1, 6], [8, 10], [15, 18]]
print(merge_intervals([[1, 4], [4, 5]]))                      # [[1, 5]]
```

---

### Q119. Implement an LRU cache. 🟡
**Explanation:** Keep items in order of use. `OrderedDict.move_to_end` marks an item as most recently used; `popitem(last=False)` evicts the least recently used. `get` and `put` are O(1).

```python
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.data = OrderedDict()

    def get(self, key):
        if key not in self.data:
            return -1
        self.data.move_to_end(key)
        return self.data[key]

    def put(self, key, value):
        if key in self.data:
            self.data.move_to_end(key)
        self.data[key] = value
        if len(self.data) > self.capacity:
            self.data.popitem(last=False)

c = LRUCache(2)
c.put(1, 1); c.put(2, 2)
print(c.get(1))     # 1
c.put(3, 3)         # evicts key 2
print(c.get(2))     # -1
c.put(4, 4)         # evicts key 1
print(c.get(1), c.get(3), c.get(4))   # -1 3 4
```

---

### Q120. Rotate an N×N matrix 90° clockwise. 🟡
**Explanation:** Transpose (rows ↔ columns), then reverse each row. `zip(*matrix)` transposes.

```python
def rotate(matrix):
    return [list(row)[::-1] for row in zip(*matrix)]

print(rotate([[1, 2, 3], [4, 5, 6], [7, 8, 9]]))
# [[7, 4, 1], [8, 5, 2], [9, 6, 3]]
```

---

### Q121. Count the number of islands in a grid. 🟡
**Explanation:** Scan the grid; when you find land (`1`), flood-fill the whole island (BFS/DFS) marking cells visited, and add one to the count. O(rows × cols).

```python
from collections import deque

def num_islands(grid):
    grid = [list(row) for row in grid]
    rows, cols = len(grid), len(grid[0])
    count = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == "1":
                count += 1
                queue = deque([(r, c)])
                grid[r][c] = "0"
                while queue:
                    x, y = queue.popleft()
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < rows and 0 <= ny < cols and grid[nx][ny] == "1":
                            grid[nx][ny] = "0"
                            queue.append((nx, ny))
    return count

print(num_islands(["11000", "11000", "00100", "00011"]))   # 3
```

---

### Q122. Reverse a singly linked list. 🟡
**Explanation:** Walk the list, pointing each node's `next` to the previous node. Keep `prev`, `cur` and save `cur.next` before overwriting it. O(n) time, O(1) space.

```python
class Node:
    def __init__(self, val, next=None):
        self.val, self.next = val, next

def from_list(values):
    head = None
    for v in reversed(values):
        head = Node(v, head)
    return head

def to_list(head):
    out = []
    while head:
        out.append(head.val)
        head = head.next
    return out

def reverse(head):
    prev = None
    while head:
        head.next, prev, head = prev, head, head.next
    return prev

print(to_list(reverse(from_list([1, 2, 3, 4]))))   # [4, 3, 2, 1]
```

---

### Q123. Shortest path in an unweighted graph (BFS). 🟡
**Explanation:** BFS explores level by level, so the first time you reach the goal you used the fewest edges. Keep a `visited` set to avoid cycles. O(V + E).

```python
from collections import deque

def shortest_path(graph, start, goal):
    queue = deque([[start]])
    visited = {start}
    while queue:
        path = queue.popleft()
        for nxt in graph[path[-1]]:
            if nxt == goal:
                return path + [nxt]
            if nxt not in visited:
                visited.add(nxt)
                queue.append(path + [nxt])
    return None

graph = {"A": ["B", "C"], "B": ["D"], "C": ["D", "E"], "D": ["F"], "E": ["F"], "F": []}
print(shortest_path(graph, "A", "F"))   # ['A', 'B', 'D', 'F']
print(shortest_path(graph, "F", "A"))   # None
```

---

### Q124. Count connected components in an undirected graph (DFS). 🟡
**Explanation:** Visit every node; whenever you reach one not yet visited, start a DFS that marks its whole component, and add one to the count.

```python
def count_components(graph):
    visited = set()
    count = 0
    for node in graph:
        if node in visited:
            continue
        count += 1
        stack = [node]
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            stack.extend(graph[cur])
    return count

graph = {1: [2], 2: [1, 3], 3: [2], 4: [5], 5: [4], 6: []}
print(count_components(graph))   # 3
```

---

### Q125. Implement merge sort (and quicksort). 🟡
**Explanation:** Merge sort splits the list, sorts halves, merges them: O(n log n) always, stable. Quicksort partitions around a pivot: O(n log n) average, O(n²) worst case.

```python
def merge_sort(a):
    if len(a) <= 1:
        return a
    mid = len(a) // 2
    left, right = merge_sort(a[:mid]), merge_sort(a[mid:])
    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            out.append(left[i]); i += 1
        else:
            out.append(right[j]); j += 1
    return out + left[i:] + right[j:]

def quick_sort(a):
    if len(a) <= 1:
        return a
    pivot = a[len(a) // 2]
    return (quick_sort([x for x in a if x < pivot])
            + [x for x in a if x == pivot]
            + quick_sort([x for x in a if x > pivot]))

data = [5, 2, 9, 1, 5, 6]
print(merge_sort(data))   # [1, 2, 5, 5, 6, 9]
print(quick_sort(data))   # [1, 2, 5, 5, 6, 9]
```

---

### Q126. Best time to buy and sell a stock once. 🟢
**Explanation:** Track the lowest price so far and the best profit if you sold today. One pass, O(n).

```python
def max_profit(prices):
    low = float("inf")
    best = 0
    for p in prices:
        low = min(low, p)
        best = max(best, p - low)
    return best

print(max_profit([7, 1, 5, 3, 6, 4]))   # 5
print(max_profit([7, 6, 4, 3, 1]))      # 0
```

---

### Q127. Longest substring without repeating characters (sliding window). 🟡
**Explanation:** Keep a window `[start, i]` with no repeats. Remember the last index of each character; when a repeat appears inside the window, move `start` just past the earlier copy. O(n).

```python
def longest_unique(s):
    last = {}
    start = best = 0
    for i, ch in enumerate(s):
        if ch in last and last[ch] >= start:
            start = last[ch] + 1
        last[ch] = i
        best = max(best, i - start + 1)
    return best

print(longest_unique("abcabcbb"))   # 3
print(longest_unique("bbbbb"))      # 1
print(longest_unique("pwwkew"))     # 3
```

---

### Q128. Convert a Roman numeral to an integer. 🟢
**Explanation:** Add each value, but subtract it if a larger value follows (IV = 4, IX = 9, XC = 90 ...).

```python
def roman_to_int(s):
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    for i, ch in enumerate(s):
        if i + 1 < len(s) and values[ch] < values[s[i + 1]]:
            total -= values[ch]
        else:
            total += values[ch]
    return total

print(roman_to_int("MCMXCIV"))   # 1994
print(roman_to_int("LVIII"))     # 58
```

---

### Q129. Generate Pascal's triangle. 🟢
**Explanation:** Each row starts and ends with 1; inner values are sums of adjacent values from the previous row.

```python
def pascal(n):
    rows = []
    for _ in range(n):
        if not rows:
            rows.append([1])
        else:
            prev = rows[-1]
            rows.append([1] + [a + b for a, b in zip(prev, prev[1:])] + [1])
    return rows

print(pascal(5))   # [[1], [1, 1], [1, 2, 1], [1, 3, 3, 1], [1, 4, 6, 4, 1]]
```

---

### Q130. Return a matrix in spiral order. 🟡
**Explanation:** Repeatedly take the first row, then rotate what remains counter-clockwise (transpose + reverse the row order) so the next side becomes the first row.

```python
def spiral(matrix):
    m = [row[:] for row in matrix]
    out = []
    while m:
        out += m.pop(0)
        m = [list(r) for r in zip(*m)][::-1]
    return out

print(spiral([[1, 2, 3], [4, 5, 6], [7, 8, 9]]))   # [1, 2, 3, 6, 9, 8, 7, 4, 5]
```

---

### Q131. Find users with at least `k` events inside a time window (sliding window over sorted times). 🟡
**Explanation:** Group event times per user and sort. If `times[i + k - 1] - times[i] <= window` for some `i`, then `k` events fit inside the window. Typical for "suspicious activity" / rate-limit questions.

```python
from collections import defaultdict

def busy_users(events, k, window):
    times = defaultdict(list)
    for user, t in events:
        times[user].append(t)
    result = []
    for user, ts in times.items():
        ts.sort()
        if any(ts[i + k - 1] - ts[i] <= window for i in range(len(ts) - k + 1)):
            result.append(user)
    return sorted(result)

events = [("ann", 1), ("bob", 2), ("ann", 3), ("ann", 5), ("bob", 20), ("bob", 40), ("cy", 1)]
print(busy_users(events, k=3, window=5))   # ['ann']
```

---

### Q132. Badge-access problem (classic Karat style): find invalid badge records. 🟡
**Explanation:** Group records by person, **sort by time as integers** (times like `"830"` and `"1355"` sort wrongly as strings), then simulate inside/outside. An exit while outside → *missing enter*. An enter while already inside, or still inside at the end → *missing exit*.

```python
from collections import defaultdict

def badge_issues(records):
    by_person = defaultdict(list)
    for name, t, action in records:
        by_person[name].append((int(t), action))

    missing_exit, missing_enter = set(), set()
    for name, events in by_person.items():
        inside = False
        for _, action in sorted(events):
            if action == "enter":
                if inside:
                    missing_exit.add(name)
                inside = True
            else:
                if not inside:
                    missing_enter.add(name)
                inside = False
        if inside:
            missing_exit.add(name)
    return sorted(missing_exit), sorted(missing_enter)

records = [
    ["Paul", "1355", "exit"], ["Paul", "1315", "enter"], ["Jennifer", "1910", "enter"],
    ["John", "830", "enter"], ["Paul", "1405", "enter"], ["John", "835", "exit"],
    ["Paul", "1630", "exit"], ["John", "855", "enter"], ["Peter", "1500", "exit"],
]
print(badge_issues(records))   # (['Jennifer', 'John'], ['Peter'])
```

---

### Q133. Meeting rooms: can one person attend all meetings, and how many rooms are needed? 🟡
**Explanation:** Sort by start time. For "attend all", check that each meeting starts after the previous ends. For minimum rooms, keep a min-heap of end times; reuse a room if the earliest-ending meeting is over.

```python
import heapq

def can_attend(meetings):
    meetings = sorted(meetings)
    return all(meetings[i][0] >= meetings[i - 1][1] for i in range(1, len(meetings)))

def min_rooms(meetings):
    ends = []
    for start, end in sorted(meetings):
        if ends and ends[0] <= start:
            heapq.heapreplace(ends, end)    # reuse the freed room
        else:
            heapq.heappush(ends, end)       # need a new room
    return len(ends)

meetings = [(0, 30), (5, 10), (15, 20)]
print(can_attend(meetings))   # False
print(min_rooms(meetings))    # 2
```

---

### Q134. Coin change: the fewest coins to make an amount (dynamic programming). 🟡
**Explanation:** `dp[a]` = fewest coins for amount `a`. For each amount try every coin: `dp[a] = min(dp[a - coin] + 1)`. O(amount × coins). Return `-1` if impossible.

```python
def coin_change(coins, amount):
    INF = float("inf")
    dp = [0] + [INF] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a:
                dp[a] = min(dp[a], dp[a - c] + 1)
    return -1 if dp[amount] == INF else dp[amount]

print(coin_change([1, 2, 5], 11))   # 3   (5 + 5 + 1)
print(coin_change([2], 3))          # -1
```

---

### Q135. Climbing stairs: in how many ways can you climb `n` steps taking 1 or 2 at a time? 🟢
**Explanation:** The ways to reach step `n` = ways to reach `n-1` + ways to reach `n-2` — the Fibonacci pattern. Keep only the last two values (O(1) space).

```python
def climb_stairs(n):
    a, b = 1, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b

print([climb_stairs(n) for n in range(1, 6)])   # [1, 2, 3, 5, 8]
```

---

### Q136. Design a stack that returns the minimum in O(1). 🟡
**Explanation:** Store each value together with the minimum seen so far.

```python
class MinStack:
    def __init__(self):
        self.stack = []                    # (value, min_so_far)

    def push(self, x):
        current_min = min(x, self.stack[-1][1]) if self.stack else x
        self.stack.append((x, current_min))

    def pop(self):
        return self.stack.pop()[0]

    def get_min(self):
        return self.stack[-1][1]

s = MinStack()
for x in [5, 3, 7, 2]:
    s.push(x)
print(s.get_min())   # 2
s.pop()
print(s.get_min())   # 3
```

---

### Q137. Binary tree: in-order traversal, maximum depth and level order. 🟡
**Explanation:** In-order = left, node, right. Depth = 1 + max(depth(left), depth(right)). Level order uses a queue (BFS).

```python
from collections import deque

class TreeNode:
    def __init__(self, val, left=None, right=None):
        self.val, self.left, self.right = val, left, right

def inorder(node):
    return inorder(node.left) + [node.val] + inorder(node.right) if node else []

def max_depth(node):
    return 1 + max(max_depth(node.left), max_depth(node.right)) if node else 0

def level_order(root):
    out, queue = [], deque([root] if root else [])
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        out.append(level)
    return out

#       1
#      / \
#     2   3
#    / \
#   4   5
root = TreeNode(1, TreeNode(2, TreeNode(4), TreeNode(5)), TreeNode(3))
print(inorder(root))        # [4, 2, 5, 1, 3]
print(max_depth(root))      # 3
print(level_order(root))    # [[1], [2, 3], [4, 5]]
```

---

### Q138. Analyse web-access log lines: top paths and server-error rate. 🟡
**Explanation:** Parse each line into fields, count with `Counter`, and compute a percentage. Always guard against division by zero for empty input.

```python
from collections import Counter

logs = [
    "GET /home 200", "GET /api/users 200", "POST /api/users 500",
    "GET /home 200", "GET /api/orders 404", "GET /home 304",
]

paths = Counter()
server_errors = 0
for line in logs:
    method, path, status = line.split()
    paths[path] += 1
    if int(status) >= 500:
        server_errors += 1

print(paths.most_common(2))                              # [('/home', 3), ('/api/users', 2)]
print(f"{server_errors / len(logs):.1%}" if logs else "0%")   # 16.7%
```

---

### Q139. Evaluate a Reverse Polish Notation expression. 🟡
**Explanation:** Scan tokens; push numbers on a stack; for an operator pop two operands (the **second** popped is the left operand), apply it and push the result. Division truncates toward zero.

```python
def eval_rpn(tokens):
    stack = []
    for t in tokens:
        if t in {"+", "-", "*", "/"}:
            b, a = stack.pop(), stack.pop()
            if t == "+":
                stack.append(a + b)
            elif t == "-":
                stack.append(a - b)
            elif t == "*":
                stack.append(a * b)
            else:
                stack.append(int(a / b))
        else:
            stack.append(int(t))
    return stack[0]

print(eval_rpn(["2", "1", "+", "3", "*"]))        # 9
print(eval_rpn(["4", "13", "5", "/", "+"]))       # 6
```

---

### Q140. Three Sum: find all unique triplets that add up to zero. 🟡
**Explanation:** Sort. Fix the first number, then use two pointers (`l`, `r`) on the rest. Skip duplicates to keep triplets unique. O(n²).

```python
def three_sum(nums):
    nums = sorted(nums)
    result = []
    for i in range(len(nums) - 2):
        if i and nums[i] == nums[i - 1]:
            continue
        l, r = i + 1, len(nums) - 1
        while l < r:
            s = nums[i] + nums[l] + nums[r]
            if s < 0:
                l += 1
            elif s > 0:
                r -= 1
            else:
                result.append([nums[i], nums[l], nums[r]])
                l += 1
                while l < r and nums[l] == nums[l - 1]:
                    l += 1
                r -= 1
    return result

print(three_sum([-1, 0, 1, 2, -1, -4]))   # [[-1, -1, 2], [-1, 0, 1]]
```

---
---

# 📊 Big-O Cheat-Sheet

| Complexity | Name | Typical example |
|---|---|---|
| O(1) | Constant | dict/set lookup, list append, index access |
| O(log n) | Logarithmic | binary search, heap push/pop |
| O(n) | Linear | one loop, `in` on a list, Counter build |
| O(n log n) | Linearithmic | `sorted`, merge sort |
| O(n²) | Quadratic | nested loops, brute-force two-sum |
| O(2ⁿ) | Exponential | naive Fibonacci, all subsets |
| O(n!) | Factorial | all permutations |

**Patterns → tools**

| If you see… | Think… |
|---|---|
| "find / count / duplicates / seen before" | `dict`, `set`, `Counter` |
| "sorted array", "find position" | binary search / `bisect` |
| "pairs / triplets in sorted data" | two pointers |
| "contiguous subarray / substring" | sliding window, prefix sums |
| "matching brackets, undo, nested" | stack |
| "shortest path, level by level" | BFS with `deque` |
| "explore all options / components" | DFS / recursion / backtracking |
| "min/max of a stream, top-k, scheduling" | `heapq` |
| "optimal count / ways, overlapping subproblems" | dynamic programming / memoization |
| "group by key, aggregate logs" | `defaultdict`, `groupby`, `Counter` |

---

# ✅ Final Checklist

- [ ] I can explain mutable vs immutable, `is` vs `==`, shallow vs deep copy.
- [ ] I know list / dict / set / tuple operations and their Big-O.
- [ ] I can write comprehensions, generators, decorators and context managers from memory.
- [ ] I can model a problem with a class (`__init__`, `__repr__`, `@property`, inheritance, ABC, dataclass).
- [ ] I handle errors with specific `except` blocks and know `finally` / `else`.
- [ ] I can parse logs/CSV/JSON and aggregate with `Counter` / `defaultdict`.
- [ ] I can solve two-pointer, sliding-window, stack, BFS/DFS, heap and basic DP problems.
- [ ] I state complexity, test edge cases (empty, one element, duplicates, negatives) and explain my choices out loud.

Good luck! 🍀
