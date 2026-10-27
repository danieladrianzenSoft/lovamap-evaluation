"""
Configuration for the API submission workflow.

Provides a `SubmissionConfig` dataclass and `load_submission_config` loader
that reads credentials from environment variables (via python-dotenv).
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_API_BASE_URL = "https://core.lovamap.com"
DEFAULT_SCAFFOLD_DIR = PROJECT_ROOT / "data" / "scaffolds" / "clean"
DEFAULT_DX = 2.0
DEFAULT_GENERATE_MESH = False
DEFAULT_POLL_INTERVAL = 3.0
DEFAULT_JOB_TIMEOUT = 120.0


@dataclass
class SubmissionConfig:
    api_base_url: str
    email: str
    password: str
    scaffold_dirs: List[Path]
    output_dir: Path
    dx: float = DEFAULT_DX
    generate_mesh: bool = DEFAULT_GENERATE_MESH
    poll_interval: float = DEFAULT_POLL_INTERVAL
    job_timeout: float = DEFAULT_JOB_TIMEOUT
    scaffold_files: Optional[List[str]] = field(default=None)

    @property
    def scaffold_dir(self) -> Path:
        """Backward compatibility: return the first scaffold directory."""
        return self.scaffold_dirs[0]


def load_submission_config(
    api_base_url: Optional[str] = None,
    scaffold_dirs: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
    dx: Optional[float] = None,
    generate_mesh: Optional[bool] = None,
    poll_interval: Optional[float] = None,
    job_timeout: Optional[float] = None,
    scaffold_files: Optional[List[str]] = None,
    # Backward compatibility
    scaffold_dir: Optional[str] = None,
) -> SubmissionConfig:
    load_dotenv()

    email = os.environ.get("LOVAMAP_EMAIL", "")
    password = os.environ.get("LOVAMAP_PASSWORD", "")
    if not email or not password:
        raise ValueError(
            "LOVAMAP_EMAIL and LOVAMAP_PASSWORD must be set in .env or environment variables."
        )

    api_url = api_base_url or DEFAULT_API_BASE_URL

    # Build list of scaffold directories
    if scaffold_dirs:
        scaffold_paths = [Path(d) for d in scaffold_dirs]
    elif scaffold_dir:
        scaffold_paths = [Path(scaffold_dir)]
    else:
        scaffold_paths = [DEFAULT_SCAFFOLD_DIR]

    if output_dir:
        out_path = Path(output_dir)
    else:
        timestamp = datetime.now().strftime("%m%d%Y")
        out_path = PROJECT_ROOT / "data" / "descriptors" / "cpp" / f"batch_{timestamp}"

    return SubmissionConfig(
        api_base_url=api_url.rstrip("/"),
        email=email,
        password=password,
        scaffold_dirs=scaffold_paths,
        output_dir=out_path,
        dx=dx if dx is not None else DEFAULT_DX,
        generate_mesh=generate_mesh if generate_mesh is not None else DEFAULT_GENERATE_MESH,
        poll_interval=poll_interval if poll_interval is not None else DEFAULT_POLL_INTERVAL,
        job_timeout=job_timeout if job_timeout is not None else DEFAULT_JOB_TIMEOUT,
        scaffold_files=scaffold_files,
    )
