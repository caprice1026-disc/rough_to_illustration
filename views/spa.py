from __future__ import annotations

from pathlib import Path

from flask import Blueprint, abort, current_app, send_from_directory


spa_bp = Blueprint("spa", __name__)


@spa_bp.route("/", defaults={"path": ""})
@spa_bp.route("/<path:path>")
def index(path: str):
    if path.startswith("api") or path.startswith("static"):
        abort(404)

    spa_root = Path(current_app.root_path) / "static" / "spa"
    return send_from_directory(spa_root, "index.html")
