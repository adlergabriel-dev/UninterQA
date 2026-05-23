from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from services.cliente_portal_service import ClientePortalService

bp = Blueprint("cliente_portal", __name__, url_prefix="/cliente")


def login_cliente_obrigatorio(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        cliente = session.get("cliente")
        if not cliente:
            flash("Faça login para acessar a área do cliente.", "warning")
            return redirect(url_for("cliente_auth.login"))
        return view(*args, **kwargs)
    return wrapper


@bp.get("/meu-cadastro")
@login_cliente_obrigatorio
def meu_cadastro():
    cliente_sessao = session.get("cliente") or {}
    cliente = ClientePortalService.buscar_por_id(cliente_sessao.get("id"))

    if not cliente:
        session.pop("cliente", None)
        flash("Sessão inválida. Faça login novamente.", "warning")
        return redirect(url_for("cliente_auth.login"))

    if not cliente.get("ativo", True):
        session.pop("cliente", None)
        flash("Seu cadastro está inativo. Entre em contato com o suporte.", "warning")
        return redirect(url_for("cliente_auth.login"))

    return render_template("cliente/meu_cadastro.html", cliente=cliente)


@bp.post("/meu-cadastro")
@login_cliente_obrigatorio
def atualizar_meu_cadastro():
    cliente_sessao = session.get("cliente") or {}
    cliente_id = cliente_sessao.get("id")

    nome = (request.form.get("nome") or "").strip()
    telefone = (request.form.get("telefone") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    cpf = (request.form.get("cpf") or "").strip()

    sucesso, mensagem, cliente = ClientePortalService.atualizar_cadastro(
        cliente_id=cliente_id,
        nome=nome,
        telefone=telefone,
        email=email,
        cpf=cpf,
    )

    if not sucesso:
        flash(mensagem, "danger")
        return render_template(
            "cliente/meu_cadastro.html",
            cliente={
                "id": cliente_id,
                "nome": nome,
                "telefone": telefone,
                "email": email,
                "cpf": cpf,
                "ativo": True,
            },
        )

    session["cliente"] = {
        "id": cliente["id"],
        "nome": cliente["nome"],
        "email": cliente["email"],
        "cpf": cliente.get("cpf", ""),
        "telefone": cliente.get("telefone", ""),
        "perfil": "CLIENTE",
    }

    flash("Cadastro atualizado com sucesso.", "success")
    return redirect(url_for("cliente_portal.meu_cadastro"))