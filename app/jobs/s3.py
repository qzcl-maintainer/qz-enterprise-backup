import os
import subprocess

from app.jobs.mounts import resolve_path


def _s3_env(cfg: dict) -> dict:
    env = os.environ.copy()
    env["AWS_ACCESS_KEY_ID"] = cfg.get("access_key") or os.environ.get("S3_ACCESS_KEY", "")
    env["AWS_SECRET_ACCESS_KEY"] = cfg.get("secret_key") or os.environ.get("S3_SECRET_KEY", "")
    env["AWS_DEFAULT_REGION"] = cfg.get("region") or os.environ.get("S3_REGION", "us-east-1")
    return env


def _s3_uri(cfg: dict, filename: str | None = None) -> str:
    prefix = cfg.get("prefix", "").strip("/")
    uri = f"s3://{cfg['bucket']}"
    if prefix:
        uri += f"/{prefix}"
    if filename:
        uri += f"/{filename}"
    return uri


def _run_aws(cmd: list[str], env: dict, log: list[str]) -> None:
    log.append(f"$ {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if proc.stdout:
        log.append(proc.stdout.rstrip())
    if proc.stderr:
        log.append(proc.stderr.rstrip())
    if proc.returncode != 0:
        raise RuntimeError(f"aws cli command failed ({proc.returncode})")


def upload_file(local_file: str, dest_cfg: dict, filename: str, log: list[str]) -> None:
    env = _s3_env(dest_cfg)
    uri = _s3_uri(dest_cfg, filename)
    _run_aws(["aws", "s3", "cp", local_file, uri], env, log)


def run_s3_job(job, log: list[str]) -> None:
    """Handles the standalone S3 Sync/Copy backup type (upload or download, copy or sync)."""
    cfg = job.backup_config
    mode = cfg.get("mode", "copy")
    direction = cfg.get("direction", "upload")

    if direction == "upload":
        with resolve_path(job.source_type, job.source_config, log) as local_path:
            env = _s3_env(job.destination_config)
            uri = _s3_uri(job.destination_config)
            cmd = ["aws", "s3", mode, local_path, uri]
            if mode == "copy":
                cmd.append("--recursive")
            _run_aws(cmd, env, log)
    else:
        with resolve_path(job.destination_type, job.destination_config, log) as local_path:
            os.makedirs(local_path, exist_ok=True)
            env = _s3_env(job.source_config)
            uri = _s3_uri(job.source_config)
            cmd = ["aws", "s3", mode, uri, local_path]
            if mode == "copy":
                cmd.append("--recursive")
            _run_aws(cmd, env, log)
