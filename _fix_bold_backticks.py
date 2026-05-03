"""Fix Yuque-style broken markdown: `**word**`** ... ** nested bold/backticks."""
import re
from pathlib import Path

FILES = [
    Path(r"c:\Users\zzxsc\Desktop\important\intern-project\trading-system-notes\交易系统开发.md"),
    Path(r"C:\Users\zzxsc\Desktop\important\high-level-C++\交易系统开发.md"),
]


def fix(text: str) -> str:
    # --- Core patterns: backtick-wrapped **word** followed by stray ** ... ** ---
    # `**NAME**`** (desc)**: -> **`NAME`（desc）**：
    text = re.sub(
        r"`\*\*([^*`]+)\*\*`\*\* \(([^)]+)\)\*\*:",
        r"**\1`（\2）**：",
        text,
    )
    # `**NAME**`** (desc)** without trailing colon on same group
    text = re.sub(
        r"`\*\*([^*`]+)\*\*`\*\* \(([^)]+)\)\*\*",
        r"**\1`（\2）**",
        text,
    )
    # `**NAME**`**：** explanation (compiler flags)
    text = re.sub(
        r"`\*\*([^*`]+)\*\*`\*\*：",
        r"**\1`：**",
        text,
    )
    # `**NAME**`** 剩余**: / `**NAME**`** 循环**:
    text = re.sub(
        r"`\*\*([^*`]+)\*\*`\*\* ([^*\n]+)\*\*:",
        r"**\1` \2**：",
        text,
    )
    # **强制绑定 (**`**--membind**`**)**: -> **强制绑定**（`--membind`）：
    text = re.sub(
        r"\*\*强制绑定 \(\*\*`\*\*([^*`]+)\*\*`\*\*\)\*\*:",
        r"**强制绑定**（`\1`）：",
        text,
    )
    text = re.sub(
        r"\*\*优先使用 \(\*\*`\*\*([^*`]+)\*\*`\*\*\)\*\*:",
        r"**优先使用**（`\1`）：",
        text,
    )
    # **1. **`**if-else**`** 语句**
    text = re.sub(
        r"\*\*(\d+)\. \*\*`\*\*([^*`]+)\*\*`\*\* ([^*\n]+)\*\*",
        r"**\1. `\2` \3**",
        text,
    )
    # **1.4**`**if constexpr**`**编译时多态**
    text = re.sub(
        r"\*\*(\d+\.\d+)\*\*`\*\*([^*`]+)\*\*`\*\*([^*\n]+)\*\*",
        r"**\1 `\2` \3**",
        text,
    )
    # **长 **`**if-else if**`** 链**
    text = re.sub(
        r"\*\*长 \*\*`\*\*([^*`]+)\*\*`\*\* ([^*\n]+)\*\*",
        r"**长 `\1` \2**",
        text,
    )
    # + **隐式 **`**inline**`** 规则**:
    text = re.sub(
        r"\+ \*\*隐式 \*\*`\*\*([^*`]+)\*\*`\*\* ([^*\n]+)\*\*:",
        r"+ **隐式 `\1` \2**：",
        text,
    )
    # - **C++17 **`**inline**`** 变量**:
    text = re.sub(
        r"- \*\*C\+\+17 \*\*`\*\*([^*`]+)\*\*`\*\* ([^*\n]+)\*\*:",
        r"- **C++17 `\1` \2**：",
        text,
    )
    # **非**`**inline**`**函数**
    text = re.sub(
        r"\*\*非\*\*`\*\*([^*`]+)\*\*`\*\*([^*\n]+)\*\*",
        r"**非 `\1` \2**",
        text,
    )
    # **（1）避免 **`**float**`** 与 **`**double**`** 混合**
    text = re.sub(
        r"\*\*（1）避免 \*\*`\*\*([^*`]+)\*\*`\*\* 与 \*\*`\*\*([^*`]+)\*\*`\*\* 混合\*\*",
        r"**（1）避免 `\1` 与 `\2` 混合**",
        text,
    )
    # **（2）避免 **`**float**`** 与 **`**int**`** 混合**
    text = re.sub(
        r"\*\*（2）避免 \*\*`\*\*([^*`]+)\*\*`\*\* 与 \*\*`\*\*([^*`]+)\*\*`\*\* 混合\*\*",
        r"**（2）避免 `\1` 与 `\2` 混合**",
        text,
    )
    # **每个线程只在自己的 **`**lock_node**`** 节点上自旋**
    text = re.sub(
        r"\*\*每个线程只在自己的 \*\*`\*\*([^*`]+)\*\*`\*\* ([^*\n]+)\*\*",
        r"**每个线程只在自己的 `\1` \2**",
        text,
    )
    # **2. **`**const T&**`**的作用**  (may contain &)
    text = re.sub(
        r"\*\*(\d+)\. \*\*`\*\*([^`]+?)\*\*`\*\*([^*\n]+)\*\*",
        r"**\1. `\2` \3**",
        text,
    )
    # **三、低效操作规避：针对取余（**`**%**`**）与类型转换**
    text = re.sub(
        r"\*\*三、低效操作规避：针对取余（\*\*`\*\*([^*`]+)\*\*`\*\*）与类型转换\*\*",
        r"**三、低效操作规避：针对取余（`\1`）与类型转换**",
        text,
    )
    # **1. 规避取余运算（**`**%**`**）：...
    text = re.sub(
        r"\*\*1\. 规避取余运算（\*\*`\*\*([^*`]+)\*\*`\*\*）：",
        r"**1. 规避取余运算（`\1`）：",
        text,
    )
    # + **乘法（**`*`**）**
    text = re.sub(
        r"\+ \*\*乘法（\*\*`\*\*([^*`]+)\*\*`\*\*）\*\*",
        r"+ **乘法（`\1`）**",
        text,
    )
    # **`**_mm_CRC32_uXX**`** 系列
    text = re.sub(
        r"\*\*1\.\*\*`\*\*([^*`]+)\*\*`\*\* 系列函数",
        r"**1. `\1` 系列函数",
        text,
    )
    text = re.sub(
        r"\*\*1\.\*\*`\*\*(_mm_CRC32_uXX)\*\*`\*\* 系列函数用作高性能的hash函数\*\*",
        r"**1. `\1` 系列函数用作高性能的hash函数**",
        text,
    )
    # Remaining `**...**`** patterns (generic second pass)
    # **X **`**Y**`** Z** -> **X `Y` Z**
    for _ in range(5):
        new_t = re.sub(
            r"\*\*([^*\n]{0,80}?) \*\*`\*\*([^*`]+)\*\*`\*\* ([^*\n]+?)\*\*",
            r"**\1 `\2` \3**",
            text,
        )
        if new_t == text:
            break
        text = new_t

    # Chained compiler flags: `**A**`** / **`**B**`**：** -> **`A` / `B`：** 
    text = re.sub(
        r"`\*\*([^*`]+)\*\*`\*\* / `\*\*([^*`]+)\*\*`\*\*：",
        r"**\1` / `\2`：**",
        text,
    )
    # `**A**`**：**text`**-fprofile-use**`**：** 
    text = re.sub(
        r"`\*\*-fprofile-use\*\*`\*\*：",
        r"**`-fprofile-use`：**",
        text,
    )
    # Fix doubled sentence pattern for profile
    text = re.sub(
        r"`\*\*-fprofile-generate\*\*`\*\*：([^`\n]+)`\*\*-fprofile-use\*\*`\*\*：",
        r"**`-fprofile-generate`：**\1**`-fprofile-use`：**",
        text,
    )

    return text


def main():
    for fp in FILES:
        if not fp.exists():
            print(f"SKIP missing: {fp}")
            continue
        raw = fp.read_text(encoding="utf-8")
        fixed = fix(raw)
        if fixed != raw:
            fp.write_text(fixed, encoding="utf-8")
            print(f"UPDATED: {fp}")
        else:
            print(f"NO CHANGE: {fp}")


if __name__ == "__main__":
    main()
