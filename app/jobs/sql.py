import gzip
import os
import shutil
import subprocess
import tempfile
from datetime import datetime

from app.jobs.mounts import resolve_path
from app.jobs.s3 import upload_file


def _dump_postgresql(cfg: dict, out_path: str, log: list[str]) -> None:
    env = os.environ.copy()
    env["PGPASSWORD"] = cfg["password"]
    cmd = [
        "pg_dump",
        "-h", cfg["host"],
        "-p", str(cfg.get("port", 5432)),
        "-U", cfg["username"],
        "-d", cfg["database"],
        "-f", out_path,
    ]
    log.append(f"$ pg_dump -h {cfg['host']} -p {cfg.get('port', 5432)} -U {cfg['username']} -d {cfg['database']} -f {out_path}")
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if proc.stderr:
        log.append(proc.stderr.rstrip())
    if proc.returncode != 0:
        raise RuntimeError(f"pg_dump failed ({proc.returncode})")


def _dump_mysql(cfg: dict, out_path: str, log: list[str]) -> None:
    cmd = [
        "mysqldump",
        "-h", cfg["host"],
        "-P", str(cfg.get("port", 3306)),
        "-u", cfg["username"],
        f"-p{cfg['password']}",
        cfg["database"],
    ]
    log.append(f"$ mysqldump -h {cfg['host']} -P {cfg.get('port', 3306)} -u {cfg['username']} -p*** {cfg['database']} > {out_path}")
    with open(out_path, "w") as fh:
        proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.PIPE, text=True)
    if proc.stderr:
        log.append(proc.stderr.rstrip())
    if proc.returncode != 0:
        raise RuntimeError(f"mysqldump failed ({proc.returncode})")


def _dump_mssql(cfg: dict, out_path: str, log: list[str]) -> None:
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={cfg['host']},{cfg.get('port', 1433)};"
        f"DATABASE={cfg['database']};UID={cfg['username']};PWD={cfg['password']};"
        f"TrustServerCertificate=yes;"
    )
    log.append(f"$ bcp {cfg['database']} out {out_path} (ODBC)")
    import pyodbc  # imported lazily so other engines don't require the driver

    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()
    cursor.execute(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'"
    )
    tables = [row[0] for row in cursor.fetchall()]
    with open(out_path, "w") as fh:
        for table in tables:
            fh.write(f"-- table: {table}\n")
            cursor.execute(f"SELECT * FROM [{table}]")
            for row in cursor.fetchall():
                values = ", ".join(repr(v) for v in row)
                fh.write(f"INSERT INTO [{table}] VALUES ({values});\n")
    log.append(f"dumped {len(tables)} table(s)")
    cnxn.close()


_DUMPERS = {
    "postgresql": _dump_postgresql,
    "mysql": _dump_mysql,
    "mssql": _dump_mssql,
}


def run_sql_backup(job, log: list[str]) -> None:
    cfg = job.backup_config
    engine = cfg["engine"]
    if engine not in _DUMPERS:
        raise ValueError(f"unsupported SQL engine: {engine}")

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"{job.name}-{timestamp}.sql"
    output_format = cfg.get("output_format", "sql")

    with tempfile.TemporaryDirectory() as tmp:
        dump_path = os.path.join(tmp, filename)
        _DUMPERS[engine](cfg, dump_path, log)

        final_path = dump_path
        if output_format == "gz":
            gz_path = dump_path + ".gz"
            with open(dump_path, "rb") as src, gzip.open(gz_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            final_path = gz_path
            filename += ".gz"

        _place_at_destination(job, final_path, filename, log)


def _place_at_destination(job, local_file: str, filename: str, log: list[str]) -> None:
    dest_type = job.destination_type
    dest_cfg = job.destination_config

    if dest_type == "s3":
        upload_file(local_file, dest_cfg, filename, log)
        return

    with resolve_path(dest_type, dest_cfg, log) as dest_dir:
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copy(local_file, os.path.join(dest_dir, filename))
        log.append(f"copied {filename} to {dest_dir}")
