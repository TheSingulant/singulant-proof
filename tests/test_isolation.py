from pathlib import Path

FORBIDDEN = (
    "ai4",
    "telegram",
    "authorize",
    "consume",
    "handoff",
    "v07",
    " r3",
    "r3.",
)


def test_repo_does_not_import_ai4_or_tx_paths() -> None:
    root = Path(__file__).resolve().parents[1]
    hits: list[str] = []
    for path in [*root.joinpath("src").rglob("*.py"), *root.joinpath("scripts").rglob("*.py")]:
        text = path.read_text(encoding="utf-8").lower()
        for token in FORBIDDEN:
            if token in text and "zero" not in text:
                # README-style isolation comments in the eval stub mention the names once.
                if path.name == "nansen_eval.py":
                    continue
                hits.append(f"{path}:{token}")
    assert hits == []
