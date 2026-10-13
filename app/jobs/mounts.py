import os
import subprocess
import tempfile
from contextlib import contextmanager

LogFn = callable


def _run(cmd: list[str], log: list[str]) -> None:
    log.append(f"$ {' '.join(a if 'password' not in a.lower() else '***' for a in cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.stdout:
        log.append(proc.stdout.rstrip())
    if proc.stderr:
        log.append(proc.stderr.rstrip())
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd)}")


@contextmanager
def resolve_path(mount_type: str, config: dict, log: list[str]):
    """Yield a local filesystem path for local/nfs/smb config, mounting network shares as needed."""
    if mount_type == "local":
        yield config["path"]
        return

    mountpoint = tempfile.mkdtemp(prefix="backup-mnt-")
    try:
        if mount_type == "nfs":
            host = config["host"]
            export_path = config["export_path"]
            options = config.get("mount_options", "")
            cmd = ["mount", "-t", "nfs"]
            if options:
                cmd += ["-o", options]
            cmd += [f"{host}:{export_path}", mountpoint]
            _run(cmd, log)
        elif mount_type == "smb":
            host = config["host"]
            share = config["share"]
            username = config.get("username", "")
            password = config.get("password", "")
            domain = config.get("domain", "")
            options = config.get("mount_options", "")
            opt_parts = [f"username={username}", f"password={password}"]
            if domain:
                opt_parts.append(f"domain={domain}")
            if options:
                opt_parts.append(options)
            cmd = ["mount", "-t", "cifs", f"//{host}/{share}", mountpoint, "-o", ",".join(opt_parts)]
            _run(cmd, log)
        else:
            raise ValueError(f"unsupported mount type: {mount_type}")

        subpath = config.get("path", "")
        yield os.path.join(mountpoint, subpath.lstrip("/")) if subpath else mountpoint
    finally:
        if os.path.ismount(mountpoint):
            subprocess.run(["umount", mountpoint], capture_output=True, text=True)
        try:
            os.rmdir(mountpoint)
        except OSError:
            pass
