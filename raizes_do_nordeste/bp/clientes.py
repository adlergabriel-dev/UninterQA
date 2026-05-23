from flask import Blueprint, render_template, request, redirect, url_for, flash

from utils.decorators import login_required, perfil_required
from services.cliente_service import ClienteService

bp = Blueprint("clientes", __name__, url_prefix="/clientes")


@bp.route("/")
@login_required
@perfil_required("ADMIN", "GERENTE", "USUARIO")
def lista():
    clientes = ClienteService.listar()

    filtro_nome = request.args.get("nome", "").strip().lower()
    filtro_telefone = request.args.get("telefone", "").strip()
    filtro_email = request.args.get("email", "").strip().lower()
    filtro_status = request.args.get("status", "").strip().upper()

    if filtro_nome:
        clientes = [
            c for c in clientes
            if filtro_nome in (c.get("nome", "") or "").lower()
        ]

    if filtro_telefone:
        clientes = [
            c for c in clientes
            if filtro_telefone in (c.get("telefone", "") or "")
        ]

    if filtro_email:
        clientes = [
            c for c in clientes
            if filtro_email in (c.get("email", "") or "").lower()
        ]

    if filtro_status:
        ativo_filtro = filtro_status == "ATIVO"
        clientes = [
            c for c in clientes
            if bool(c.get("ativo", False)) == ativo_filtro
        ]

    filtros = {
        "nome": request.args.get("nome", "").strip(),
        "telefone": request.args.get("telefone", "").strip(),
        "email": request.args.get("email", "").strip(),
        "status": request.args.get("status", "").strip(),
    }

    return render_template("clientes/lista.html", clientes=clientes, filtros=filtros)


@bp.route("/novo", methods=["GET", "POST"])
@login_required
@perfil_required("ADMIN", "GERENTE", "USUARIO")
def novo():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()

        if not nome:
            flash("O nome do cliente é obrigatório.", "warning")
            return render_template("clientes/form.html", cliente=request.form)

        if not telefone:
            flash("O telefone do cliente é obrigatório.", "warning")
            return render_template("clientes/form.html", cliente=request.form)

        ClienteService.criar(request.form)
        flash("Cliente cadastrado com sucesso.", "success")
        return redirect(url_for("clientes.lista"))

    return render_template("clientes/form.html", cliente=None)


@bp.route("/editar/<cliente_id>", methods=["GET", "POST"])
@login_required
@perfil_required("ADMIN", "GERENTE", "USUARIO")
def editar(cliente_id):
    cliente = ClienteService.buscar_por_id(cliente_id)

    if not cliente:
        flash("Cliente não encontrado.", "danger")
        return redirect(url_for("clientes.lista"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()

        if not nome:
            flash("O nome do cliente é obrigatório.", "warning")
            return render_template("clientes/form.html", cliente=request.form)

        if not telefone:
            flash("O telefone do cliente é obrigatório.", "warning")
            return render_template("clientes/form.html", cliente=request.form)

        ClienteService.atualizar(cliente_id, request.form)
        flash("Cliente atualizado com sucesso.", "success")
        return redirect(url_for("clientes.lista"))

    return render_template("clientes/form.html", cliente=cliente)


@bp.route("/status/<cliente_id>/<acao>")
@login_required
@perfil_required("ADMIN", "GERENTE")
def alterar_status(cliente_id, acao):
    ativo = acao == "ativar"
    ClienteService.alterar_status(cliente_id, ativo)
    flash("Status do cliente alterado com sucesso.", "success")
    return redirect(url_for("clientes.lista"))