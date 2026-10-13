import os
import shutil
import subprocess

from app.jobs.mounts import resolve_path


def _xcopy(src: str, dst: str, log: list[str]) -> None:
    """Additive-only copy: creates/overwrites files, never deletes anything at the destination."""
    copied = 0
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        dest_root = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(dest_root, exist_ok=True)
        for f in files:
            shutil.copy2(os.path.join(root, f), os.path.join(dest_root, f))
            copied += 1
    log.append(f"xcopy: copied {copied} file(s) from {src} to {dst}")


def _rsync(src: str, dst: str, delete: bool, log: list[str]) -> None:
    src_arg = src.rstrip("/") + "/"
    dst_arg = dst.rstrip("/") + "/"
    cmd = ["rsync", "-a"]
    if delete:
        cmd.append("--delete")
    cmd += [src_arg, dst_arg]
    log.append(f"$ {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.stdout:
        log.append(proc.stdout.rstrip())
    if proc.stderr:
        log.append(proc.stderr.rstrip())
    if proc.returncode != 0:
        raise RuntimeError(f"rsync failed ({proc.returncode})")


def run_filecopy_job(job, log: list[str]) -> None:
    cfg = job.backup_config
    mode = cfg.get("mode", "rsync")
    delete = bool(cfg.get("delete", False))

    with resolve_path(job.source_type, job.source_config, log) as src, resolve_path(
        job.destination_type, job.destination_config, log
    ) as dst:
        os.makedirs(dst, exist_ok=True)
        if mode == "xcopy":
            _xcopy(src, dst, log)
        elif mode == "rsync":
            _rsync(src, dst, delete, log)
        else:
            raise ValueError(f"unsupported file copy mode: {mode}")
