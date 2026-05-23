from flask import Blueprint, render_template

from utils.decorators import login_required, perfil_required
from services.auditoria_service import AuditoriaService

bp = Blueprint("auditoria", __name__, url_prefix="/auditoria")


@bp.route("/")
@login_required
@perfil_required("ADMIN")
def lista():
    eventos = AuditoriaService.listar()

    return render_template(
        "auditoria/lista.html",
        eventos=eventos,
    )