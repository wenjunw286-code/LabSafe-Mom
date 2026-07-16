from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib import error, request


ROOT = Path(__file__).resolve().parent
DEFAULT_PROTOCOL_DIR = ROOT / "protocols"


@dataclass
class CaseResult:
    filename: str
    report_id: int | None
    status: str
    upload_s: float
    analysis_s: float
    total_s: float
    overall_risk: str | None = None
    overall_score: int | None = None
    substances: int | None = None
    error: str | None = None


def http_json(url: str, method: str = "GET", body: bytes | None = None, headers: dict | None = None) -> dict:
    req = request.Request(url, data=body, method=method, headers=headers or {})
    with request.urlopen(req, timeout=120) as resp:
        data = resp.read().decode("utf-8")
        return json.loads(data) if data else {}


def upload_file(api_url: str, path: Path) -> dict:
    boundary = "----LabSafeMomBoundary" + uuid.uuid4().hex
    mime = mimetypes.guess_type(path.name)[0] or "text/plain"
    content = path.read_bytes()
    parts = [
        f"--{boundary}\r\n".encode(),
        (
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8"),
        content,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    body = b"".join(parts)
    return http_json(
        f"{api_url}/upload",
        method="POST",
        body=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )


def trigger_analysis(api_url: str, report_id: int) -> dict:
    body = json.dumps({"population": "pregnancy"}).encode("utf-8")
    return http_json(
        f"{api_url}/analyze/{report_id}",
        method="POST",
        body=body,
        headers={"Content-Type": "application/json"},
    )


def wait_for_completion(api_url: str, report_id: int, timeout_s: int = 180) -> str:
    deadline = time.monotonic() + timeout_s
    delay = 0.5
    while time.monotonic() < deadline:
        status = http_json(f"{api_url}/analyze/{report_id}/status")
        state = status.get("status", "unknown")
        if state in {"completed", "failed"}:
            return state
        time.sleep(delay)
        delay = min(delay * 1.4, 5.0)
    return "timeout"


def fetch_report(api_url: str, report_id: int) -> dict:
    return http_json(f"{api_url}/report/{report_id}")


def run_case(api_url: str, path: Path) -> CaseResult:
    start = time.monotonic()
    report_id: int | None = None
    try:
        t0 = time.monotonic()
        upload = upload_file(api_url, path)
        upload_s = time.monotonic() - t0
        report_id = int(upload["id"])

        t1 = time.monotonic()
        trigger_analysis(api_url, report_id)
        status = wait_for_completion(api_url, report_id)
        analysis_s = time.monotonic() - t1

        if status != "completed":
            return CaseResult(
                filename=path.name,
                report_id=report_id,
                status=status,
                upload_s=upload_s,
                analysis_s=analysis_s,
                total_s=time.monotonic() - start,
                error=f"analysis ended with status={status}",
            )

        report = fetch_report(api_url, report_id)
        exec_summary = report.get("executive_summary", {})
        return CaseResult(
            filename=path.name,
            report_id=report_id,
            status=status,
            upload_s=upload_s,
            analysis_s=analysis_s,
            total_s=time.monotonic() - start,
            overall_risk=report.get("overall_risk"),
            overall_score=report.get("overall_score"),
            substances=exec_summary.get("total_substances_found"),
        )
    except (error.URLError, error.HTTPError, KeyError, ValueError, TimeoutError) as exc:
        return CaseResult(
            filename=path.name,
            report_id=report_id,
            status="error",
            upload_s=0.0,
            analysis_s=0.0,
            total_s=time.monotonic() - start,
            error=str(exc),
        )


async def run_all(api_url: str, files: list[Path], concurrency: int, repeat: int) -> list[CaseResult]:
    sem = asyncio.Semaphore(concurrency)
    queue = [path for _ in range(repeat) for path in files]

    async def one(path: Path) -> CaseResult:
        async with sem:
            return await asyncio.to_thread(run_case, api_url, path)

    return await asyncio.gather(*(one(path) for path in queue))


def print_results(results: list[CaseResult]) -> None:
    print("\nfilename,status,id,risk,score,substances,upload_s,analysis_s,total_s,error")
    for r in results:
        print(
            f"{r.filename},{r.status},{r.report_id or ''},{r.overall_risk or ''},"
            f"{r.overall_score if r.overall_score is not None else ''},"
            f"{r.substances if r.substances is not None else ''},"
            f"{r.upload_s:.2f},{r.analysis_s:.2f},{r.total_s:.2f},{r.error or ''}"
        )

    completed = [r for r in results if r.status == "completed"]
    if completed:
        avg_total = sum(r.total_s for r in completed) / len(completed)
        max_total = max(r.total_s for r in completed)
        print(f"\ncompleted={len(completed)}/{len(results)} avg_total_s={avg_total:.2f} max_total_s={max_total:.2f}")
    else:
        print(f"\ncompleted=0/{len(results)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--protocol-dir", type=Path, default=DEFAULT_PROTOCOL_DIR)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()

    files = sorted(args.protocol_dir.glob("*.txt"))
    if not files:
        raise SystemExit(f"No .txt files found in {args.protocol_dir}")

    results = asyncio.run(run_all(args.api_url.rstrip("/"), files, max(1, args.concurrency), max(1, args.repeat)))
    print_results(results)


if __name__ == "__main__":
    main()

