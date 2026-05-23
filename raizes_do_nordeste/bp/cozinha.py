from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from services.pedidos_admin_service import PedidosAdminService


bp = Blueprint("cozinha", __name__, url_prefix="/cozinha")


def login_interno_obrigatorio(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        usuario = session.get("usuario")
        if not usuario:
            flash("Faça login para acessar a cozinha.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapper


def perfil_interno_obrigatorio(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        usuario = session.get("usuario") or {}
        perfil = (usuario.get("perfil") or "").upper()

        if perfil not in ["ADMIN", "GERENTE", "USUARIO"]:
            flash("Você não tem permissão para acessar este módulo.", "danger")
            return redirect(url_for("home.index"))

        return view(*args, **kwargs)
    return wrapper


def _usuario_nome_logado():
    usuario = session.get("usuario") or {}
    return usuario.get("nome") or usuario.get("email") or "USUARIO_INTERNO"


def _filtrar_pedidos_operacionais(pedidos):
    pedidos = pedidos or []
    return [
        pedido
        for pedido in pedidos
        if not pedido.get("fechado_em_caixa")
    ]


def _agrupar_pedidos(pedidos):
    grupos = {
        "recebidos": [],
        "em_preparo": [],
        "prontos": [],
    }

    for pedido in pedidos:
        status = (pedido.get("status") or "").upper()

        if status == PedidosAdminService.STATUS_ABERTO:
            grupos["recebidos"].append(pedido)

        elif status == PedidosAdminService.STATUS_EM_PREPARO:
            grupos["em_preparo"].append(pedido)

        elif status in [
            PedidosAdminService.STATUS_PRONTO,
            PedidosAdminService.STATUS_ENVIADO,
        ]:
            grupos["prontos"].append(pedido)

    return grupos


@bp.get("/")
@login_interno_obrigatorio
@perfil_interno_obrigatorio
def index():
    filtros = {
        "unidade_id": (request.args.get("unidade_id") or "").strip(),
        "origem": (request.args.get("origem") or "").strip().upper(),
    }

    pedidos = PedidosAdminService.listar_pedidos_cozinha(filtros=filtros)
    pedidos = _filtrar_pedidos_operacionais(pedidos)

    grupos = _agrupar_pedidos(pedidos)
    unidades = PedidosAdminService.listar_unidades_ativas()
    origem_opcoes = PedidosAdminService.listar_origens()

    dashboard = {
        "total": len(pedidos),
        "recebidos": len(grupos["recebidos"]),
        "em_preparo": len(grupos["em_preparo"]),
        "prontos": len(grupos["prontos"]),
    }

    return render_template(
        "cozinha/index.html",
        filtros=filtros,
        pedidos=pedidos,
        grupos=grupos,
        dashboard=dashboard,
        unidades=unidades,
        origem_opcoes=origem_opcoes,
    )


@bp.post("/<pedido_id>/status")
@login_interno_obrigatorio
@perfil_interno_obrigatorio
def alterar_status(pedido_id):
    pedido_atual = PedidosAdminService.buscar_pedido_por_id(pedido_id)

    if not pedido_atual:
        flash("Pedido não encontrado.", "warning")
        return redirect(url_for("cozinha.index"))

    if pedido_atual.get("fechado_em_caixa"):
        flash("Este pedido já está fechado no caixa e não pode ser alterado pela cozinha.", "danger")
        return redirect(url_for("cozinha.index"))

    novo_status = (request.form.get("novo_status") or "").strip().upper()

    sucesso, mensagem, pedido = PedidosAdminService.alterar_status_pedido(
        pedido_id=pedido_id,
        novo_status=novo_status,
        usuario_nome=_usuario_nome_logado(),
    )

    flash(mensagem, "success" if sucesso else "danger")

    return redirect(url_for("cozinha.index"))