"""
LOVAMAP Core API client and submission orchestrator.

Handles authentication, job submission, polling, and result download.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from config.submission import SubmissionConfig


# ---------- API helpers ----------

def authenticate(cfg: SubmissionConfig) -> str:
    """POST /users/connect → JWT token."""
    url = f"{cfg.api_base_url}/users/connect"
    resp = requests.post(url, json={"email": cfg.email, "password": cfg.password})
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise ValueError("Authentication succeeded but no token returned.")
    return token


def submit_job(
    cfg: SubmissionConfig,
    token: str,
    file_path: Path,
    job_id: str,
) -> Dict[str, Any]:
    """POST /jobs — multipart form-data with scaffold file."""
    url = f"{cfg.api_base_url}/jobs"
    headers = {"Authorization": f"Bearer {token}"}

    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f)}
        data = {
            "jobId": job_id,
            "dx": str(cfg.dx),
            "generateMesh": str(cfg.generate_mesh).lower(),
        }
        resp = requests.post(url, headers=headers, files=files, data=data)

    resp.raise_for_status()
    return resp.json()


def check_job_status(cfg: SubmissionConfig, token: str, job_id: str) -> Dict[str, Any]:
    """GET /jobs/by-jobid/{jobId} → job status object."""
    url = f"{cfg.api_base_url}/jobs/by-jobid/{job_id}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()


def get_raw_results(cfg: SubmissionConfig, token: str, job_id: str) -> Dict[str, Any]:
    """GET /jobs/{jobId}/raw-results → raw descriptor JSON."""
    url = f"{cfg.api_base_url}/jobs/{job_id}/raw-results"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()


# ---------- Polling ----------

# API job status codes
STATUS_COMPLETED = 2
STATUS_FAILED = 3


def poll_until_complete(
    cfg: SubmissionConfig,
    token: str,
    job_id: str,
) -> Dict[str, Any]:
    """Poll job status until completed or failed, with timeout."""
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > cfg.job_timeout:
            raise TimeoutError(
                f"Job {job_id} timed out after {cfg.job_timeout:.0f}s"
            )

        status_resp = check_job_status(cfg, token, job_id)
        status_code = status_resp.get("status")

        if status_code == STATUS_COMPLETED:
            return status_resp
        if status_code == STATUS_FAILED:
            error_msg = status_resp.get("error", "Unknown error")
            raise RuntimeError(f"Job {job_id} failed: {error_msg}")

        time.sleep(cfg.poll_interval)


# ---------- Orchestrator ----------

def _resolve_scaffold_files(cfg: SubmissionConfig) -> List[Path]:
    """Find scaffold files to submit."""
    if cfg.scaffold_files:
        files = []
        for name in cfg.scaffold_files:
            # Check across all scaffold dirs
            for d in cfg.scaffold_dirs:
                path = d / name
                if path.exists():
                    files.append(path)
                    break
            else:
                print(f"  [WARN] Scaffold file not found: {name}")
        return files

    # All .dat and .json files across all scaffold dirs
    files = []
    for d in cfg.scaffold_dirs:
        files.extend(d.glob("*.dat"))
        files.extend(d.glob("*.json"))
    return sorted(files)


def _output_filename(scaffold_path: Path) -> str:
    """Determine output filename: .dat → .json, .json stays .json."""
    if scaffold_path.suffix == ".dat":
        return scaffold_path.stem + ".json"
    return scaffold_path.name


def run_submission(cfg: SubmissionConfig) -> Dict[str, Any]:
    """
    Orchestrate: authenticate → submit each file → poll → download → save.

    Returns a summary dict with 'output_dir' and 'results' list.
    """
    print("=== LOVAMAP API Submission Workflow ===")
    print(f"  API URL      : {cfg.api_base_url}")
    for d in cfg.scaffold_dirs:
        print(f"  Scaffold dir : {d}")
    print(f"  Output dir   : {cfg.output_dir}")
    print(f"  dx           : {cfg.dx}")
    print(f"  Generate mesh: {cfg.generate_mesh}")
    print(f"  Poll interval: {cfg.poll_interval}s")
    print(f"  Job timeout  : {cfg.job_timeout}s")
    print()

    # 1. Authenticate
    print("Authenticating...")
    try:
        token = authenticate(cfg)
    except requests.HTTPError as e:
        print(f"[ERROR] Authentication failed: {e}")
        return {"output_dir": str(cfg.output_dir), "results": []}
    print("  Authenticated successfully.\n")

    # 2. Resolve scaffold files
    scaffold_files = _resolve_scaffold_files(cfg)
    if not scaffold_files:
        print("[WARN] No scaffold files found to submit.")
        return {"output_dir": str(cfg.output_dir), "results": []}

    print(f"Found {len(scaffold_files)} scaffold file(s) to submit:")
    for f in scaffold_files:
        print(f"  - {f.name}")
    print()

    # 3. Process each file
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []

    for scaffold_path in scaffold_files:
        out_name = _output_filename(scaffold_path)
        out_path = cfg.output_dir / out_name

        # Resume support: skip files whose output already exists
        if out_path.exists():
            print(f"--- {scaffold_path.name} --- SKIPPED (output exists: {out_name})")
            results.append({"file": scaffold_path.name, "job_id": "", "status": "skipped", "output": str(out_path)})
            continue

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_id = f"{scaffold_path.stem}_{timestamp}"

        print(f"--- {scaffold_path.name} ---")
        print(f"  Job ID: {job_id}")

        # Submit (with automatic re-auth on 401)
        try:
            print("  Submitting...")
            try:
                submit_job(cfg, token, scaffold_path, job_id)
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 401:
                    print("  Token expired, re-authenticating...")
                    token = authenticate(cfg)
                    submit_job(cfg, token, scaffold_path, job_id)
                else:
                    raise
            print("  Submitted. Polling for completion...")
        except (requests.HTTPError, requests.ConnectionError) as e:
            print(f"  [ERROR] Submission failed: {e}")
            results.append({"file": scaffold_path.name, "job_id": job_id, "status": "submit_failed", "error": str(e)})
            continue

        # Poll (with automatic re-auth on 401)
        try:
            try:
                poll_until_complete(cfg, token, job_id)
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 401:
                    print("  Token expired, re-authenticating...")
                    token = authenticate(cfg)
                    poll_until_complete(cfg, token, job_id)
                else:
                    raise
            print("  Job completed.")
        except (TimeoutError, RuntimeError, requests.HTTPError, requests.ConnectionError) as e:
            print(f"  [ERROR] {e}")
            results.append({"file": scaffold_path.name, "job_id": job_id, "status": "failed", "error": str(e)})
            continue

        # Download results (with automatic re-auth on 401)
        try:
            print("  Downloading results...")
            try:
                raw = get_raw_results(cfg, token, job_id)
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 401:
                    print("  Token expired, re-authenticating...")
                    token = authenticate(cfg)
                    raw = get_raw_results(cfg, token, job_id)
                else:
                    raise
            out_path = cfg.output_dir / out_name
            with open(out_path, "w") as f:
                json.dump(raw, f, indent=2)
            print(f"  Saved to: {out_path}")
            results.append({"file": scaffold_path.name, "job_id": job_id, "status": "success", "output": str(out_path)})
        except (requests.HTTPError, requests.JSONDecodeError, requests.ConnectionError, ValueError) as e:
            print(f"  [ERROR] Failed to download results: {e}")
            results.append({"file": scaffold_path.name, "job_id": job_id, "status": "download_failed", "error": str(e)})

        print()

    # Summary
    succeeded = sum(1 for r in results if r["status"] == "success")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = len(results) - succeeded - skipped
    print(f"=== Submission Complete: {succeeded} succeeded, {skipped} skipped, {failed} failed ===")

    return {"output_dir": str(cfg.output_dir), "results": results}
