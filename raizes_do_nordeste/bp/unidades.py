from flask import Blueprint, render_template, request, redirect, url_for, flash

from utils.decorators import login_required, perfil_required
from services.unidade_service import UnidadeService

bp = Blueprint("unidades", __name__, url_prefix="/unidades")


@bp.route("/")
@login_required
@perfil_required("ADMIN", "GERENTE")
def lista():
    unidades = UnidadeService.listar()

    filtro_nome = request.args.get("nome", "").strip().lower()
    filtro_codigo = request.args.get("codigo", "").strip().lower()
    filtro_cidade = request.args.get("cidade", "").strip().lower()
    filtro_estado = request.args.get("estado", "").strip().upper()
    filtro_status = request.args.get("status", "").strip().upper()

    if filtro_nome:
        unidades = [
            u for u in unidades
            if filtro_nome in (u.get("nome", "") or "").lower()
        ]

    if filtro_codigo:
        unidades = [
            u for u in unidades
            if filtro_codigo in (u.get("codigo", "") or "").lower()
        ]

    if filtro_cidade:
        unidades = [
            u for u in unidades
            if filtro_cidade in (u.get("cidade", "") or "").lower()
        ]

    if filtro_estado:
        unidades = [
            u for u in unidades
            if (u.get("estado", "") or "").upper() == filtro_estado
        ]

    if filtro_status:
        ativo_filtro = filtro_status == "ATIVA"
        unidades = [
            u for u in unidades
            if bool(u.get("ativo", False)) == ativo_filtro
        ]

    filtros = {
        "nome": request.args.get("nome", "").strip(),
        "codigo": request.args.get("codigo", "").strip(),
        "cidade": request.args.get("cidade", "").strip(),
        "estado": request.args.get("estado", "").strip(),
        "status": request.args.get("status", "").strip(),
    }

    return render_template("unidades/lista.html", unidades=unidades, filtros=filtros)


@bp.route("/nova", methods=["GET", "POST"])
@login_required
@perfil_required("ADMIN", "GERENTE")
def nova():
    if request.method == "POST":
        UnidadeService.criar(request.form)
        flash("Unidade cadastrada com sucesso.", "success")
        return redirect(url_for("unidades.lista"))

    return render_template("unidades/form.html", unidade=None)


@bp.route("/editar/<unidade_id>", methods=["GET", "POST"])
@login_required
@perfil_required("ADMIN", "GERENTE")
def editar(unidade_id):
    unidade = UnidadeService.buscar_por_id(unidade_id)

    if not unidade:
        flash("Unidade não encontrada.", "danger")
        return redirect(url_for("unidades.lista"))

    if request.method == "POST":
        UnidadeService.atualizar(unidade_id, request.form)
        flash("Unidade atualizada com sucesso.", "success")
        return redirect(url_for("unidades.lista"))

    return render_template("unidades/form.html", unidade=unidade)


@bp.route("/status/<unidade_id>/<acao>")
@login_required
@perfil_required("ADMIN", "GERENTE")
def alterar_status(unidade_id, acao):
    ativo = acao == "ativar"
    UnidadeService.alterar_status(unidade_id, ativo)
    flash("Status da unidade alterado com sucesso.", "success")
    return redirect(url_for("unidades.lista"))