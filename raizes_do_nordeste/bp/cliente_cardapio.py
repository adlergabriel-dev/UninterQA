from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from services.cliente_cardapio_service import ClienteCardapioService

bp = Blueprint("cliente_cardapio", __name__, url_prefix="/cliente")


def login_cliente_obrigatorio(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        cliente = session.get("cliente")
        if not cliente:
            flash("Faça login para acessar a área do cliente.", "warning")
            return redirect(url_for("cliente_auth.login"))
        return view(*args, **kwargs)
    return wrapper


@bp.get("/cardapio")
@login_cliente_obrigatorio
def cardapio():
    cliente_sessao = session.get("cliente") or {}

    unidade_id = (request.args.get("unidade_id") or "").strip()
    termo = (request.args.get("termo") or "").strip()

    cliente = ClienteCardapioService.buscar_cliente_por_id(cliente_sessao.get("id"))
    if not cliente:
        session.pop("cliente", None)
        flash("Sessão inválida. Faça login novamente.", "warning")
        return redirect(url_for("cliente_auth.login"))

    if not cliente.get("ativo", True):
        session.pop("cliente", None)
        flash("Seu cadastro está inativo. Entre em contato com o suporte.", "warning")
        return redirect(url_for("cliente_auth.login"))

    unidades = ClienteCardapioService.listar_unidades_ativas()
    itens = ClienteCardapioService.listar_cardapio_publico(
        unidade_id=unidade_id,
        termo=termo,
    )

    return render_template(
        "cliente/cardapio.html",
        cliente=cliente,
        unidades=unidades,
        itens=itens,
        filtros={
            "unidade_id": unidade_id,
            "termo": termo,
        },
    )