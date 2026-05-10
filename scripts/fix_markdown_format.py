#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Normalize recurring Markdown emphasis / inline-code glitches across the four
project docs (Chinese + English + high-level-C++ mirrors).

Design goals
------------
1. **Fence-aware**: replacements run only outside ``` fenced blocks, so code
   samples are not altered.
2. **Image-link safe**: inside non-fence Markdown, standard `![alt](url)` spans
   are temporarily masked so literal/regex fixes cannot alter URL text. (Urls that
   contain a raw `)` before the real closing parenthesis are ambiguous in
   Markdown and are not masked end-to-end—avoid adding rules that match inside
   those rare forms.)
3. **Explicit rule registry**: every change has an id + human description;
   extend SUBSTITUTIONS / REGEX_RULES rather than ad-hoc edits.
4. **Idempotent**: safe to re-run; rules should not fight each other.
5. **Deterministic order**: literals first (longest/most specific before generic),
   then compiled regex rules in REGEX_RULES order.

Do **not** add broad patterns meant to “clean up” arbitrary OCR dumps; keep new
rules narrowly keyed to known duplicated headings/phrases so pasted OCR lines
stay verbatim unless they exactly match an intentional fix string.

Usage
-----
    python scripts/fix_markdown_format.py [--dry-run] [--no-backup]
    python scripts/fix_markdown_format.py --notes-only
    python scripts/fix_markdown_format.py --files path1.md path2.md

Optional aggressive mode (may need review):
    python scripts/fix_markdown_format.py --aggressive-missing-space-after-bold

Exit code 1 if any target file is missing.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Callable, List, NamedTuple, Tuple

# ---------------------------------------------------------------------------
# Paths (trading-system-notes is the repo containing this script)
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent

NOTES_REPO_TARGETS: List[Path] = [
    _REPO_ROOT / "交易系统开发.md",
    _REPO_ROOT / "README.md",
]

DEFAULT_TARGETS: List[Path] = NOTES_REPO_TARGETS + [
    _REPO_ROOT.parent / "high-level-C++" / "交易系统开发.md",
    _REPO_ROOT.parent / "high-level-C++" / "README.md",
]


def split_fenced_segments(text: str) -> List[Tuple[str, str]]:
    """
    Split into alternating ('md' | 'fence', chunk).
    A fence starts at ``` and ends at the next ``` on a later line (minimal heuristic).
    """
    segments: List[Tuple[str, str]] = []
    pos = 0
    n = len(text)
    while pos < n:
        idx = text.find("```", pos)
        if idx == -1:
            segments.append(("md", text[pos:]))
            break
        segments.append(("md", text[pos:idx]))
        line_end = text.find("\n", idx)
        if line_end == -1:
            segments.append(("fence", text[idx:]))
            break
        nxt = text.find("```", line_end + 1)
        if nxt == -1:
            segments.append(("fence", text[idx:]))
            break
        segments.append(("fence", text[idx : nxt + 3]))
        pos = nxt + 3
    return segments


def join_segments(segments: List[Tuple[str, str]]) -> str:
    return "".join(chunk for _, chunk in segments)


def transform_outside_fences(text: str, fn: Callable[[str], str]) -> str:
    segs = split_fenced_segments(text)
    out: List[Tuple[str, str]] = []
    for kind, chunk in segs:
        out.append((kind, fn(chunk) if kind == "md" else chunk))
    return join_segments(out)


# Placeholder must never appear in repo Markdown (PUA). Holds masked image lines.
_IMG_PLACEHOLDER_PREFIX = "\U000f0000MDIMG"
_IMG_PLACEHOLDER_SUFFIX = "\U000f0001"

# `![alt](url)` — url runs to first `)`; sufficient for typical CDN/Yuque links.
_MD_IMAGE_INLINE = re.compile(r"!\[[^\]]*\]\([^)]*\)")


def mask_markdown_inline_images(md_chunk: str) -> Tuple[str, List[str]]:
    """Replace each inline image span with a placeholder; return originals for restore."""
    originals: List[str] = []

    def repl(_m: re.Match[str]) -> str:
        originals.append(_m.group(0))
        i = len(originals) - 1
        return f"{_IMG_PLACEHOLDER_PREFIX}{i}{_IMG_PLACEHOLDER_SUFFIX}"

    return _MD_IMAGE_INLINE.sub(repl, md_chunk), originals


def unmask_markdown_inline_images(md_chunk: str, originals: List[str]) -> str:
    for i, src in enumerate(originals):
        md_chunk = md_chunk.replace(
            f"{_IMG_PLACEHOLDER_PREFIX}{i}{_IMG_PLACEHOLDER_SUFFIX}", src
        )
    return md_chunk


class SubRule(NamedTuple):
    rule_id: str
    description: str
    old: str
    new: str


class RegexRule(NamedTuple):
    rule_id: str
    description: str
    pattern: str
    repl: str
    flags: int = 0


# ---------------------------------------------------------------------------
# Literal replacements (apply in order; keep specific strings before generic)
# ---------------------------------------------------------------------------
SUBSTITUTIONS: List[SubRule] = [
    # --- Corrupted PGO / paste artifacts ---
    SubRule(
        "pgo-literal-backslash-n",
        "Turn literal `\\n++ ` (broken paste) into real newline + bullet.",
        ").\\n++ ",
        ").\n\n+ ",
    ),
    # --- Chinese: broken quadruple asterisk around inline (mirror fixes) ---
    SubRule(
        "zh-cpp17-inline-var",
        "Fix `C++17 ****inline` typo.",
        "    - **C++17 ****inline` 变量**： 允许在头文件中定义全局变量，确保其在整个程序中的唯一性（如 `inline AppConfig cfg;`）。",
        "    - **C++17 `inline` 变量**：允许在头文件中定义全局变量，确保其在整个程序中的唯一性（如 `inline AppConfig cfg;`）。",
    ),
    SubRule(
        "zh-implicit-inline-rule",
        "Fix `隐式 ****inline` typo.",
        "+ **隐式 ****inline` 规则**：",
        "+ **隐式 `inline` 规则**：",
    ),
    # --- Compiler hint bullets (English README mirror) ---
    SubRule(
        "hint-restrict",
        "Normalize __restrict__ bullet.",
        "+ `__restrict__`** Keyword (C/C++): ** Used to tell the compiler that the memory regions pointed to by pointers do not overlap (aliasing problems), which allows the compiler to confidently perform optimizations such as loop vectorization and code movement without inserting expensive runtime alias checks.",
        "+ **`__restrict__` keyword (C/C++):** Tells the compiler that pointer targets do not alias, enabling aggressive optimizations without runtime alias checks.",
    ),
    SubRule(
        "hint-unroll",
        "Normalize pragma unroll bullet.",
        "+ `#pragma unroll(N)`** / `#pragma clang loop vectorize(enable)`:** Forces the compiler to unroll or vectorize a loop even if its cost model deems it unhelpful. This is useful in certain scenarios where human judgment is more accurate than the compiler.",
        "+ **`#pragma unroll(N)` / `#pragma clang loop vectorize(enable)`:** Forces unrolling or vectorization even when the cost model disagrees.",
    ),
    SubRule(
        "hint-likely",
        "Normalize [[likely]] / [[unlikely]] bullet.",
        "+ `[[likely]]`** / `[[unlikely]]` Property (C++20): ** Used to prompt the compiler to predict conditional branches. The compiler optimizes the machine code layout based on these hints, placing the most frequently executed code paths together, thus reducing the penalty for branch mispredictions.",
        "+ **`[[likely]]` / `[[unlikely]]` (C++20):** Branch prediction hints; the compiler may lay out hot paths to reduce misprediction cost.",
    ),
    SubRule(
        "hint-builtin-parity",
        "Normalize __builtin_parity bullet.",
        "+ `__builtin_parity(x)`**(GCC)**: Count the parity of the number of 1's in x (odd numbers return 1, even numbers return 0), used for error detection (such as checksum);",
        "+ **`__builtin_parity(x)` (GCC):** Returns parity of the popcount of `x` (odd → 1, even → 0); useful for checksums.",
    ),
    SubRule(
        "perf-tools-bullet",
        "Normalize perf bullet.",
        "+ `perf`**Tools**: Sampling CPU cycles, cache miss rate, branch prediction failure rate, etc., and locating hot functions (such as through`perf record -g`Analyze the call stack).",
        "+ **`perf`:** Samples cycles, cache misses, branch mispredictions, etc.; locate hot code (e.g. `perf record -g` + stack analysis).",
    ),
    SubRule(
        "prefetch-hints-heading",
        "Normalize _mm_prefetch hints line.",
        "`_mm_prefetch`** hints** ([Intel Intrinsics Guide](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html)):",
        "**`_mm_prefetch` hints** ([Intel Intrinsics Guide](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html)):",
    ),
    # --- CRC heading ---
    SubRule(
        "crc32-heading",
        "Normalize CRC32 intrinsic heading.",
        "**1. **`_mm_CRC32_uXX`** series function**: Used as a high-performance hash function",
        "**1. `_mm_CRC32_uXX` family:** Used as a high-performance hash primitive.",
    ),
    # --- Spin lock / MCS prose ---
    SubRule(
        "while-cycle-label",
        "Fix `while`** cycle** label.",
        "2. `while`** cycle**: if only `compare_exchange_weak` return `false`(Indicating that the lock was not grabbed), the cycle will continue. Because after failure `zero` The value will be changed to `locked` current value (1), so it must be reset to `0`, so that you can continue to try \"replace 0 with 1\".",
        "2. **`while` loop**: if only `compare_exchange_weak` returns `false` (indicating that the lock was not grabbed), the loop will continue. Because after failure `zero` The value will be changed to `locked` current value (1), so it must be reset to `0`, so that you can continue to try \"replace 0 with 1\".",
    ),
    SubRule(
        "mcs-queue-prose",
        "Rewrite MCS queue paragraph (bold/backtick glue).",
        "The MCS lock organizes a queue (logical linked list) of waiting threads. Each thread wishing to acquire a lock assigns one of its own `lock_node` The node is added to the end of the queue. Then,**Each thread is only in its own **`lock_node`** spin on node**, wait for the previous thread to release the lock and notify it.",
        "The MCS lock organizes a queue (logical linked list) of waiting threads. Each thread wishing to acquire a lock enqueues its own `lock_node`. Then, **each thread spins only on its own `lock_node`**, waiting for the predecessor to release the lock and hand off.",
    ),
    SubRule(
        "mcs-own-spin",
        "Fix `it's**own**` glue before node->locked.",
        "5. Finally, it's**own**`node->locked` Spin on the logo. This is crucial because each thread spins on a different memory address, avoiding cache contention.",
        "5. Finally, it spins on its own `node->locked` flag. This is crucial because each thread spins on a different cache line, reducing coherence traffic.",
    ),
    # --- rdtsc instrumentation bullets ---
    SubRule(
        "rdtsc-bullet",
        "Normalize rdtsc description bullet.",
        "4. `rdtsc`**Function**: Using assembly instructions `rdtsc` Read the value from the TSC register, combining the lower 32 bits and upper 32 bits into a 64-bit `uint64_t` Type value representing elapsed CPU clock cycles. This is the basis of the entire performance instrumentation and is used to obtain the precise number of CPU clock cycles.",
        "4. **`rdtsc`:** Uses the `rdtsc` instruction to read the TSC, combining low and high halves into a 64-bit `uint64_t` count of elapsed CPU cycles—the basis of this instrumentation.",
    ),
    SubRule(
        "start-measure-bullet",
        "Normalize START_MEASURE bullet.",
        "5. `START_MEASURE`** Macro **: Use this macro where you need to start measuring latency, it will call `rdtsc` The function gets the current number of CPU clock cycles and creates a file with the specified name (`TAG`) to store this value in a constant variable for subsequent calculation of the delay.",
        "5. **`START_MEASURE` macro:** At the start of a latency measurement, calls `rdtsc` and stores the cycle count in a constant named `TAG` for later differencing.",
    ),
    SubRule(
        "end-measure-bullet",
        "Normalize END_MEASURE bullet.",
        "6. `END_MEASURE`** Macro **: Use this macro where you need to end the measured delay, it calls again `rdtsc` The function gets the current number of CPU clock cycles, calculates the difference from the value stored when the measurement was started, gets the number of delayed CPU clock cycles, and passes it to the logger (`LOGGER`) records the current time string and delay value.",
        "6. **`END_MEASURE` macro:** At the end of a measurement, calls `rdtsc` again, subtracts the stored start count, and logs the delta via `LOGGER`.",
    ),
    SubRule(
        "ttt-measure-bullet",
        "Normalize TTT_MEASURE bullet.",
        "7. `TTT_MEASURE`**Macro**: used to record the current timestamp (in nanoseconds), by calling `Common::getCurrentNanos()` The function gets the current time and then uses a logger to log the current time string and that time value.",
        "7. **`TTT_MEASURE` macro:** Records the current timestamp in nanoseconds (`Common::getCurrentNanos()`) and logs it.",
    ),
    # --- Arithmetic / type sections ---
    SubRule(
        "mul-div-headings",
        "Simplify multiplication/division reminder headings.",
        "+ **Multiplication(**`*`**)**: The latency of integer multiplication is about 4-6 times that of integer addition, and the latency of floating-point multiplication is even higher;",
        "+ **Multiplication (`*`):** Integer multiply latency is roughly 4–6× that of add; floating-point multiply costs more still.",
    ),
    SubRule(
        "div-rem-long",
        "Shorten division bullet lead-in (keep trailing sentence).",
        "+ **Division(**`/`) and remainder (`%`**)**: The latency of division in the CPU is 10-20 times that of multiplication, and the latency of remainder operations (especially remainders of powers other than 2) is even higher. When the divisor is a compile-time constant, the compiler automatically converts division/modulo into multiplication + shift ([Barrett reduction](https://en.wikipedia.org/wiki/Division_algorithm)), but cannot optimize when the divisor is only known at runtime. If the same divisor will be used repeatedly, use [libdivide](https://libdivide.com/) to precompute the multiplication constant at runtime; using the divisor as a compile-time constant in a switch-case also triggers this optimization ([whichisfaster.dev/modulo](https://whichisfaster.dev/q/modulo.html));",
        "+ **Division (`/`) and remainder (`%`):** Division is often 10–20× slower than multiply; remainder with non-power-of-two divisors is especially costly at runtime (compile-time divisors can be strength-reduced). When the divisor is a compile-time constant, the compiler automatically converts division/modulo into multiplication + shift ([Barrett reduction](https://en.wikipedia.org/wiki/Division_algorithm)), but cannot optimize when the divisor is only known at runtime. If the same divisor will be used repeatedly, use [libdivide](https://libdivide.com/) to precompute the multiplication constant at runtime; using the divisor as a compile-time constant in a switch-case also triggers this optimization ([whichisfaster.dev/modulo](https://whichisfaster.dev/q/modulo.html));",
    ),
    SubRule(
        "remainder-heading-3",
        "Normalize remainder subsection heading.",
        "**3. Avoidance of inefficient operations: for remainder (**`%`**) with type conversion**",
        "**3. Avoid inefficient remainder (`%`) with implicit conversions**",
    ),
    SubRule(
        "remainder-heading-1",
        "Normalize remainder avoidance heading.",
        "**1. Avoid remainder operation (**`%`**): Replace with branches or bit operations**",
        "**1. Avoid remainder (`%`): use branches or bit tricks where applicable**",
    ),
    SubRule(
        "float-double-mix",
        "Normalize float/double mix heading.",
        "**(1)Avoid **`float`** and **`double`** mix**",
        "**(1) Avoid mixing `float` and `double`**",
    ),
    SubRule(
        "float-int-mix",
        "Normalize float/int mix heading.",
        "**(2)Avoid **`float`** and **`int`** mix**",
        "**(2) Avoid mixing `float` and `int`**",
    ),
    SubRule(
        "static-cast-table-cell",
        "Fix static_cast table cell glue.",
        "| **Use**`static_cast`   **Perform explicit conversion and avoid implicit conversion** | Explicit conversion avoids potential errors caused by C-style casts and the performance loss of implicit conversions |",
        "| **Use `static_cast` for explicit conversion (avoid implicit conversion)** | Explicit conversion avoids potential errors caused by C-style casts and the performance loss of implicit conversions |",
    ),
    SubRule(
        "large-objects-constref",
        "Fix const& bullet numbering/glue.",
        "    1. **For large objects**`const&`**Transfer**: For parameters that do not need to be modified, use \"`const Type&`\" pass to avoid copying, e.g.`void process(const Matrix& mat)`;\n2.**Small type direct value transfer**: Yes`int`,`float`For scalar types, the cost of value transfer is equivalent to that of reference transfer (or even faster, avoiding pointer indirect access), and there is no need to force the use of references;\n    2. **Avoid temporary object passing**: Pass constants to reference parameters (such as`process(5)`), the compiler will automatically create a temporary object. If you need to pass constants frequently, you can overload the function to adapt constant parameters (such as`void process(int val)`).",
        "    1. **For large objects, use `const&`:** For parameters that do not need to be modified, use `const Type&` to avoid copying, e.g. `void process(const Matrix& mat)`;\n    2. **Small types: pass by value:** For scalars such as `int` and `float`, pass-by-value cost is comparable to references (or faster); references are optional.\n    3. **Avoid unnecessary temporaries with reference parameters:** Passing constants to reference parameters (e.g. `process(5)`) creates temporaries; overload value parameters when appropriate (e.g. `void process(int val)`).",
    ),
    # --- Move semantics headings ---
    SubRule(
        "const-ref-binding-heading",
        "Fix const T& heading.",
        "**2. **`const T&`**Function**",
        "**2. `const T&` binding**",
    ),
    SubRule(
        "rvalue-binding-heading",
        "Fix T&& heading.",
        "**3. **`T&&`**Function**",
        "**3. `T&&` binding**",
    ),
    SubRule(
        "breakthrough-constref",
        "Fix breakthrough const T& line.",
        "**breakthrough**`const T&`**Limitations**: Realize \"taking over\" rather than \"borrowing\" temporary object resources.",
        "**Beyond `const T&` limitations:** Take over temporary object resources rather than only borrowing them.",
    ),
    # --- CQRS / diagram bullets ---
    SubRule(
        "cqrs-left-log",
        "Space around bold for left column CQRS bullet.",
        "+ On the left is**Full Event Log**(Record \"what happened\");",
        "+ On the left is **full event log** (records \"what happened\").",
    ),
    SubRule(
        "cqrs-right-state",
        "Space around bold for right column CQRS bullet.",
        "+ On the right is**Current status reconstructed from logs**(Documenting \"what it's like now\").",
        "+ On the right is **current state reconstructed from logs** (describes \"what it is now\").",
    ),
    # --- FIX example ---
    SubRule(
        "fix-example-body",
        "Normalize FIX NewOrderSingle example lead-in.",
        "+ **Example:**`NewOrderSingle (35=D)`** The message body may contain: **",
        "+ **Example (`NewOrderSingle`, 35=D):** the body may contain:",
    ),
    SubRule(
        "fix-msgtype-sentence",
        "Normalize MsgType sentence if old OCR form present.",
        "The message body contains specific business data of this specific message type. Its content is completely determined by **in the message header**`MsgType (35)` Decide.",
        "The message body contains business fields for this message type; which fields appear is determined by **`MsgType (35)`** in the header.",
    ),
    # --- CTP / MySQL bullets ---
    SubRule(
        "ctp-main-cpp",
        "Normalize main.cpp bullet.",
        "+ **Main process control (**`main.cpp`**)**:",
        "+ **Main process control (`main.cpp`):**",
    ),
    SubRule(
        "ctp-mysql-utils",
        "Normalize mysql_utils bullet (two occurrences same pattern).",
        "+ **MySQL connection management (**`mysql_utils.hpp`**)**:",
        "+ **MySQL connection management (`mysql_utils.hpp`):**",
    ),
    SubRule(
        "ctp-tables",
        "Normalize table-creation bullet.",
        "+ **Table creation statements for four core tables (**`mysql_utils.hpp`**)**:",
        "+ **Table creation statements for four core tables (`mysql_utils.hpp`):**",
    ),
    # --- Rate limiter headings ---
    SubRule(
        "ratelimit-api-a",
        "Normalize ApiRateLimiter heading.",
        "**A) **`ApiRateLimiter`**(Shard Lock + Token Bucket, general production version)**",
        "**A) `ApiRateLimiter` (shard lock + token bucket, general production version)**",
    ),
    SubRule(
        "ratelimit-lockfree-b",
        "Normalize LockFreeApiRateLimiter heading (add closing **).",
        "**B) **`LockFreeApiRateLimiter`(No lock + GCRA + fixed capacity table)",
        "**B) `LockFreeApiRateLimiter` (no lock + GCRA + fixed-capacity table)**",
    ),
    # --- Strategy / permutation ---
    SubRule(
        "perf-eval-interface-heading",
        "Normalize performance evaluation interface heading.",
        "**(5)Performance evaluation interface:**`trade_system_criter`",
        "**(5) Performance evaluation interface:** `trade_system_criter`",
    ),
    SubRule(
        "permutation-opening",
        "Normalize permutation test opening sentence when OCR glued.",
        "Replacement test passed**Randomly rearrange sample labels**(such as the positive and negative marks of transaction income), destroy the potential correlation in the original data, generate an \"uncorrelated\" reference distribution, and then judge the statistical significance of the original data. In trading systems, it is often used to verify \"whether the strategy returns are significantly better than random\":",
        "A **permutation test** randomly permutes sample labels (such as the positive/negative marks of transaction income), destroying correlations present in the original data and yielding an \"uncorrelated\" reference distribution; you then assess whether the original statistic is extreme relative to that null. In trading systems this often answers whether strategy returns are materially better than random:",
    ),
    # --- Gemini monitor headings ---
    SubRule(
        "gemini-orderbook-heading",
        "Normalize orderbook.py heading.",
        "**1. Order book data structure (**`orderbook.py`**)**:",
        "**1. Order book data structure (`orderbook.py`)**:",
    ),
    SubRule(
        "gemini-ws-heading",
        "Normalize gemini_client heading.",
        "**2. WebSocket Client (**`gemini_client.py`**)**:",
        "**2. WebSocket client (`gemini_client.py`)**:",
    ),
    SubRule(
        "gemini-main-heading",
        "Normalize main.py heading.",
        "**3. Main program (**`main.py`**)**:",
        "**3. Main program (`main.py`)**:",
    ),
    SubRule(
        "gemini-strategy-file",
        "Normalize last_minute_buyer heading.",
        "`last_minute_buyer_15min.py`**(Core Strategy & Trading Logic)**",
        "**`last_minute_buyer_15min.py` (core strategy & trading logic)**",
    ),
    # --- Feature engine corrupted heading (English README) ---
    SubRule(
        "feature-engine-title",
        "Repair FeatureEngine subsection title glue (OCR-style ** / ` interleaving).",
        "2. **Feature engine working mechanism and **`**mkt_price_**`**、**`**agg_trade_qty_ratio_**`**The meaning and function**",
        "2. **Feature engine working mechanism** — meaning and role of `mkt_price_` and `agg_trade_qty_ratio_`",
    ),
    # --- README: spaced bold / OCR glue (narrow literals; preserve image URLs verbatim) ---
    SubRule(
        "micro-batch-dynamic-sizing",
        "Fix passes**Dynamically… glued phrase.",
        "Therefore, this processor passes**Dynamically adjust batch size**, automatically select the optimal strategy based on the current message queue backlog:",
        "Therefore, this processor **dynamically adjusts batch size** and automatically selects the optimal strategy based on the current message queue backlog:",
    ),
    SubRule(
        "cache-prefetch-lede-glue",
        "Space after bold before sentence (cache prefetch paragraph).",
        "**cache prefetch**Is a hardware or software technology that loads data from slower main memory into the faster CPU cache in advance before it is officially requested by the CPU.",
        "**Cache prefetch** is a hardware or software technology that loads data from slower main memory into the faster CPU cache in advance before it is officially requested by the CPU.",
    ),
    SubRule(
        "simd-img-vectorization-glue",
        "Fix image line: **vectorization** glued to following sentence (URL unchanged).",
        "![](https://cdn.nlark.com/yuque/0/2025/png/35485470/1753491708830-db9b5c2b-9a45-43a8-b14d-3baf38c25974.png)**vectorization**It is an optimization technology that uses the SIMD hardware unit in the CPU to process multiple data elements in parallel. Modern CPUs (such as SSE, AVX, AVX-512 of x86 architecture; NEON of ARM architecture) all contain SIMD instruction sets.",
        "![](https://cdn.nlark.com/yuque/0/2025/png/35485470/1753491708830-db9b5c2b-9a45-43a8-b14d-3baf38c25974.png)**Vectorization** is an optimization technology that uses the SIMD hardware unit in the CPU to process multiple data elements in parallel. Modern CPUs (such as SSE, AVX, AVX-512 of x86 architecture; NEON of ARM architecture) all contain SIMD instruction sets.",
    ),
    SubRule(
        "compiler-friendly-loops-bold-glue",
        "Spaces around glued bold phrases (vectorization tips).",
        "1. **Write concise, compiler-friendly loops**: avoid complex control flow and pointer aliases, let**auto-vectorization**and**Hardware prefetching**Make the most of it. This is the most basic and important step.",
        "1. **Write concise, compiler-friendly loops**: avoid complex control flow and pointer aliases; let **auto-vectorization** and **hardware prefetching** make the most of it. This is the most basic and important step.",
    ),
    SubRule(
        "builtin-manual-rewrite-glue",
        "Space before bold (built-in functions sentence).",
        "4. **last resort**: Only consider using it for core code segments with extreme performance requirements.**built-in functions**Do a manual rewrite.",
        "4. **Last resort**: Only consider using it for core code segments with extreme performance requirements — **built-in functions** require a manual rewrite.",
    ),
    SubRule(
        "vector-add-instruction-glue",
        "Fix a**vector addition instructions** glue.",
        "The CPU can execute a**vector addition instructions**, this instruction can perform addition operations on these 8 integers at the same time.",
        "The CPU can execute **vector addition instructions**; this instruction can perform addition operations on these 8 integers at the same time.",
    ),
    SubRule(
        "ticket-lock-cache-contention-glue",
        "Minimal spacing/grammar on ticket-lock OCR paragraph.",
        "    - **Cache contention still exists**: Like the Test-and-Set lock, all waiting threads are**same one**Atomic variables `head` Spin on. when `unlock` Revise `head` , it will also invalidate all cache lines waiting for the core, causing bus traffic. Although slightly better than implementation one (because `unlock` The operation itself is fast), but does not scale well under high contention as an MCS lock.",
        "    - **Cache contention still exists**: Like the Test-and-Set lock, all waiting threads spin on the **same** atomic variable `head`. When `unlock` revises `head`, it also invalidates peer cores' cache lines, causing bus traffic. Although slightly better than implementation one (because `unlock` itself is fast), it still does not scale well under high contention compared with an MCS lock.",
    ),
    SubRule(
        "spin-speculative-glue",
        "Fix CPU meeting**speculatively** glued bullet.",
        "+ CPU meeting**speculatively**Start executing the instructions in the loop body.",
        "+ The CPU may **speculatively** start executing the instructions in the loop body.",
    ),
    SubRule(
        "memory-order-violation-glue",
        "Fix logic**memory ordering violation** glued bullet.",
        "+ This conflict is detected once (potentially) by the CPU's internal logic**memory ordering violation**. To correct this error and strictly adhere to the memory consistency model, the CPU triggers a deeper and more expensive pipeline flush.",
        "+ This conflict is detected once (potentially) by the CPU's internal logic as a **memory ordering violation**. To correct this error and strictly adhere to the memory consistency model, the CPU triggers a deeper and more expensive pipeline flush.",
    ),
    SubRule(
        "pause-command-heading-glue",
        "Fix **PAUSE command** glued to following sentence.",
        "**PAUSE command** It is an assembly instruction used to optimize spin-wait loops.",
        "The **PAUSE** instruction is an assembly instruction used to optimize spin-wait loops.",
    ),
    SubRule(
        "bitfield-critical-path-glue",
        "Space before bold (bitfields paragraph).",
        "Bitfields are only used for**Memory/Storage Critical Path**, and recommend:",
        "Bitfields are only used for **memory/storage critical paths**; recommendations:",
    ),
    SubRule(
        "roofline-procedures-bold-glue",
        "Insert missing spaces in Roofline OCR sentence (keep wording).",
        "Roofline model talks about procedures**Under the constraints of the two indicators of computing power and bandwidth of the computing platform, the upper bound of the theoretical performance that can be achieved**, rather than the actual achieved performance, because during the actual calculation**There are other important factors besides computing power and bandwidth**, they will also affect the actual performance of the model, which is not taken into account by the Roofline Model.",
        "The Roofline model talks about procedures **under the constraints of the two indicators of computing power and bandwidth of the computing platform, the upper bound of the theoretical performance that can be achieved**, rather than the actual achieved performance, because during the actual calculation **there are other important factors besides computing power and bandwidth**; they also affect the actual performance of the model, which is not taken into account by the Roofline Model.",
    ),
    SubRule(
        "fsm-state-item-glue",
        "FSM list item: State / exclusivity spacing.",
        "1. **State**Represents the specific state of an object at a certain moment and is the basic unit of FSM. For example, the status of the order is \"new order\", \"processing\", \"cancelled\", etc. status has**exclusivity**: The object can only be in one state at the same time.",
        "1. **State** represents the specific state of an object at a certain moment and is the basic unit of FSM. For example, the status of the order is \"new order\", \"processing\", \"cancelled\", etc. Status has **exclusivity**: the object can only be in one state at the same time.",
    ),
    SubRule(
        "fsm-event-item-glue",
        "FSM list item: Event spacing.",
        "2. **Event**An external or internal signal that triggers a state transition. Events such as \"Order Success\" and \"Order Cancellation Instruction\" will push the state machine to switch from the current state to the new state.",
        "2. **Event**: an external or internal signal that triggers a state transition. Events such as \"Order Success\" and \"Order Cancellation Instruction\" will push the state machine to switch from the current state to the new state.",
    ),
    SubRule(
        "fsm-transition-item-glue",
        "FSM list item: Transition spacing.",
        "3. **Transition**Rules that define how \"current state + event\" maps to \"next state\". For example: after the \"Processing\" state receives the \"Order Completed\" event, it transitions to the \"Successful\" state.",
        "3. **Transition**: rules that define how \"current state + event\" maps to \"next state\". For example: after the \"Processing\" state receives the \"Order Completed\" event, it transitions to the \"Successful\" state.",
    ),
    SubRule(
        "fsm-action-item-glue",
        "FSM list item: Action spacing.",
        "4. **Action**Specific actions to perform during state transitions (optional). For example, recording logs when canceling orders, updating order status, etc.",
        "4. **Action**: specific actions to perform during state transitions (optional). For example, recording logs when canceling orders, updating order status, etc.",
    ),
    SubRule(
        "fsm-guard-item-glue",
        "FSM list item: Guard spacing.",
        "5. **Guard**Conditions for state transition (optional). Events trigger state transitions only when conditions are met. For example, order cancellation is only allowed if the order cancellation interval exceeds 5 seconds.",
        "5. **Guard**: conditions for state transition (optional). Events trigger state transitions only when conditions are met. For example, order cancellation is only allowed if the order cancellation interval exceeds 5 seconds.",
    ),
    SubRule(
        "memory-order-violation-bold-glue",
        "Fix logic**memory ordering violation** (spin-wait / MOB section).",
        "+ This conflict is detected once (potentially) by the CPU's internal logic**memory ordering violation**. To correct this error and strictly adhere to the memory consistency model, the CPU triggers a deeper and more expensive pipeline flush.",
        "+ This conflict is detected once (potentially) by the CPU as a **memory ordering violation**. To correct this error and strictly adhere to the memory consistency model, the CPU triggers a deeper and more expensive pipeline flush.",
    ),
]

SUBSTITUTIONS.extend(
    [
        SubRule(
            "mkt-price-subheading",
            "Normalize mkt_price_ subheading.",
            "`mkt_price_`**The meaning and function**",
            "**`mkt_price_` — meaning and function**",
        ),
        SubRule(
            "agg-ratio-subheading",
            "Normalize agg_trade_qty_ratio_ subheading.",
            "`agg_trade_qty_ratio_`**The meaning and function**",
            "**`agg_trade_qty_ratio_` — meaning and function**",
        ),
    ]
)


# ---------------------------------------------------------------------------
# Regex rules (run after literals)
# ---------------------------------------------------------------------------
REGEX_RULES: List[RegexRule] = [
    RegexRule(
        "compiler-flag-plus-backtick-bold-colon",
        "Normalize `+ `-foo`**:` → `+ **`-foo`:**` (entire `-foo` inside one inline-code span).",
        r"(?m)^\+ `([^`\n]+)`\*\*:",
        r"+ **`\1`:**",
    ),
    RegexRule(
        "sub-bullet-compiler-flag",
        "Normalize `    - `-foo`**:` → `    - **`-foo`:**`.",
        r"(?m)^(\s+)- `([^`\n]+)`\*\*:",
        r"\1- **`\2`:**",
    ),
]


def apply_substitutions(md_chunk: str) -> str:
    for rule in SUBSTITUTIONS:
        if rule.old in md_chunk:
            md_chunk = md_chunk.replace(rule.old, rule.new)
    return md_chunk


def apply_regex_rules(md_chunk: str) -> str:
    for rule in REGEX_RULES:
        md_chunk = re.sub(rule.pattern, rule.repl, md_chunk, flags=rule.flags)
    return md_chunk


def aggressive_missing_space_after_closing_bold(md_chunk: str) -> str:
    """
    If `**...**` is immediately followed by ASCII letter or '(' without space, insert one.
    Narrow: closing `**` must not be preceded by another `*` on the left neighbor.
    """
    return re.sub(r"\*\*([^\n*]+?)\*\*(?=[A-Za-z\(])", r"**\1** ", md_chunk)


def process_file(path: Path, dry_run: bool, backup: bool, aggressive: bool) -> Tuple[int, List[str]]:
    """Returns (1 if file would/did change else 0, log_lines)."""
    if not path.is_file():
        return 0, [f"[skip] missing: {path}"]

    raw = path.read_text(encoding="utf-8")
    original = raw

    def pipeline(chunk: str) -> str:
        # Literals first so rules may match full `![](url)...` lines; then mask URLs
        # before regex / aggressive passes.
        chunk = apply_substitutions(chunk)
        chunk, img_orig = mask_markdown_inline_images(chunk)
        chunk = apply_regex_rules(chunk)
        if aggressive:
            chunk = aggressive_missing_space_after_closing_bold(chunk)
        chunk = unmask_markdown_inline_images(chunk, img_orig)
        return chunk

    updated = transform_outside_fences(raw, pipeline)
    changed = 1 if original != updated else 0

    log: List[str] = []
    if original != updated:
        log.append(f"[write] {path}")
        if backup and not dry_run:
            bak = path.with_suffix(path.suffix + ".bak")
            bak.write_text(original, encoding="utf-8")
            log.append(f"        backup -> {bak}")
        if not dry_run:
            path.write_text(updated, encoding="utf-8")
    else:
        log.append(f"[ok]    {path} (no changes)")

    return changed, log


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Fix Markdown emphasis/format glitches (fence-aware).")
    parser.add_argument("--dry-run", action="store_true", help="Report only; do not write.")
    parser.add_argument("--no-backup", action="store_true", help="Skip .bak copy before overwrite.")
    parser.add_argument(
        "--aggressive-missing-space-after-bold",
        action="store_true",
        help="Insert space after **…** when glued to ASCII letter or '(' (review diffs).",
    )
    parser.add_argument(
        "--notes-only",
        action="store_true",
        help="Only process 交易系统开发.md and README.md in this repo (skip high-level-C++ mirrors).",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        default=[str(p) for p in DEFAULT_TARGETS],
        help="Explicit Markdown paths (default: four docs including high-level-C++ if present).",
    )
    args = parser.parse_args(argv)

    if args.notes_only:
        targets = [p.resolve() for p in NOTES_REPO_TARGETS]
    else:
        targets = [Path(f).resolve() for f in args.files]
    any_missing = False
    total_changed = 0
    for p in targets:
        changed, lines = process_file(
            p,
            dry_run=args.dry_run,
            backup=not args.no_backup,
            aggressive=args.aggressive_missing_space_after_bold,
        )
        total_changed += changed
        for line in lines:
            print(line)
        if "[skip]" in "".join(lines):
            any_missing = True

    if args.dry_run:
        print(f"\nDry run complete. Files that would change: {total_changed}")
    else:
        print(f"\nDone. Files modified: {total_changed}")

    return 1 if any_missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
