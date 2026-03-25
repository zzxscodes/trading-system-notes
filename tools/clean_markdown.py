import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def clean_markdown(text: str) -> str:
    # Remove HTML font/span tags (common from HTML->MD conversion)
    text = re.sub(r"</\s*(font|span)\s*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<\s*(font|span)\b[^>]*>", "", text, flags=re.IGNORECASE)

    # Remove leftover style attributes on any remaining tags (if any)
    text = re.sub(r'\sstyle\s*=\s*"[^"]*"', "", text, flags=re.IGNORECASE)
    text = re.sub(r"\sstyle\s*=\s*'[^']*'", "", text, flags=re.IGNORECASE)

    # Collapse pathological sequences of asterisks introduced by conversion:
    # - "***" or "****..." -> "**" (keep plain Markdown bold as the max)
    text = re.sub(r"\*{3,}", "**", text)

    # Common artifact: stray bold open/close separated by spaces (e.g. "**  \n****Title**")
    text = re.sub(r"^\*\*\s*$", "", text, flags=re.MULTILINE)

    # Normalize excessive spaces left by tag removal
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" \n", "\n", text)

    return text


def main() -> None:
    targets = [
        ROOT / "README.md",
        ROOT / "交易系统开发.md",
    ]

    for path in targets:
        original = path.read_text(encoding="utf-8")
        cleaned = clean_markdown(original)
        if cleaned != original:
            path.write_text(cleaned, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()

