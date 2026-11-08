"""
BN-183 / NF-05: automatic and regular backup of the data, and restoration
of a backup after a control.

A backup is a zip file containing the data (Django JSON dump, independent of
the database engine) and the uploaded documents (media).
"""

import io
import json
import os
import zipfile
from pathlib import Path

from django.conf import settings
from django.core import management
from django.utils import timezone

from .models import get_int_setting

EXCLUDED = [
    "contenttypes",
    "auth.permission",
    "sessions",
    "admin.logentry",
    "token_blacklist",
]


def backup_dir():
    path = Path(getattr(settings, "BACKUP_ROOT", Path(settings.BASE_DIR) / "backups"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_backup(include_media=True):
    stamp = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    target = backup_dir() / f"hrms-{stamp}.zip"
    data = io.StringIO()
    management.call_command(
        "dumpdata", exclude=EXCLUDED, natural_foreign=True, indent=None, stdout=data
    )
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("data.json", data.getvalue())
        archive.writestr(
            "meta.json",
            json.dumps({"created_at": timezone.now().isoformat(), "version": 1}),
        )
        media = Path(settings.MEDIA_ROOT)
        if include_media and media.exists():
            for file in media.rglob("*"):
                if file.is_file():
                    archive.write(file, f"media/{file.relative_to(media).as_posix()}")
    _rotate()
    return target


def _rotate():
    keep = get_int_setting("BACKUP_KEEP", 30)
    backups = sorted(backup_dir().glob("hrms-*.zip"))
    for old in backups[:-keep] if keep > 0 else []:
        old.unlink(missing_ok=True)


def list_backups():
    return [
        {
            "name": f.name,
            "size": f.stat().st_size,
            "created_at": timezone.datetime.fromtimestamp(
                f.stat().st_mtime, tz=timezone.get_current_timezone()
            ),
        }
        for f in sorted(backup_dir().glob("hrms-*.zip"), reverse=True)
    ]


def check_backup(path):
    """The control before a restoration: readable archive, valid data, counts."""
    path = Path(path)
    if not path.exists() or path.parent.resolve() != backup_dir().resolve():
        raise ValueError("Unknown backup.")
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"The archive is damaged ({bad}).")
        objects = json.loads(archive.read("data.json"))
        counts = {}
        for obj in objects:
            counts[obj["model"]] = counts.get(obj["model"], 0) + 1
        media = [n for n in archive.namelist() if n.startswith("media/")]
    return {
        "name": path.name,
        "objects": len(objects),
        "models": counts,
        "media_files": len(media),
    }


def restore_backup(path):
    """Replace the current data by the backup (after check_backup)."""
    report = check_backup(path)
    with zipfile.ZipFile(path) as archive:
        data = archive.read("data.json")
        tmp = backup_dir() / "_restore.json"
        tmp.write_bytes(data)
        try:
            management.call_command("flush", interactive=False, verbosity=0)
            management.call_command("loaddata", str(tmp), verbosity=0)
        finally:
            tmp.unlink(missing_ok=True)
        media_root = Path(settings.MEDIA_ROOT)
        for name in archive.namelist():
            if name.startswith("media/") and not name.endswith("/"):
                target = (media_root / name[len("media/") :]).resolve()
                if media_root.resolve() not in target.parents:
                    continue  # never write outside the media folder
                os.makedirs(target.parent, exist_ok=True)
                target.write_bytes(archive.read(name))
    return report
