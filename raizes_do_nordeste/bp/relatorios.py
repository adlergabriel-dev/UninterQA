from flask import Blueprint, render_template


bp = Blueprint(
    "relatorios",
    __name__,
    url_prefix="/relatorios"
)


@bp.route("/", methods=["GET"])
def index():
    return render_template("relatorios/index.html")