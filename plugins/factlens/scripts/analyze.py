from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path


def _project_root() -> Path:
    configured = os.environ.get("FACTLENS_PROJECT_ROOT")
    plugin_root = Path(__file__).resolve().parents[1]
    candidates = [
        plugin_root / "vendor",
        Path(configured) if configured else None,
    ]
    for candidate in candidates:
        if candidate and (candidate / "factlens" / "pipeline.py").is_file():
            return candidate
    raise RuntimeError(
        "FactLens 엔진을 찾지 못했습니다. 플러그인을 다시 설치하거나 FACTLENS_PROJECT_ROOT를 설정해 주세요."
    )


def main() -> None:
    root = _project_root()
    sys.path.insert(0, str(root))

    from factlens.models import AnalyzeRequest
    from factlens.pipeline import AnalysisPipeline

    payload = json.load(sys.stdin)
    request = AnalyzeRequest.from_dict(payload, today=date.today().isoformat())
    result = AnalysisPipeline().analyze(request)
    json.dump(result.to_dict(), sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        json.dump({"error": str(error)}, sys.stdout, ensure_ascii=False)
        raise SystemExit(1)
