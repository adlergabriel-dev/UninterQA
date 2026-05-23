from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from services.pedidos_admin_service import PedidosAdminService

bp = Blueprint("pedidos_admin", __name__, url_prefix="/pedidos-admin")


def login_interno_obrigatorio(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        usuario = session.get("usuario")
        if not usuario:
            flash("Faça login para acessar a área interna.", "warning")
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


def _voltar_para_lista():
    return redirect(request.referrer or url_for("pedidos_admin.lista"))


@bp.get("/")
@login_interno_obrigatorio
@perfil_interno_obrigatorio
def lista():
    filtros = {
        "codigo_pedido": (request.args.get("codigo_pedido") or "").strip(),
        "cliente_nome": (request.args.get("cliente_nome") or "").strip(),
        "unidade_id": (request.args.get("unidade_id") or "").strip(),
        "status": (request.args.get("status") or "").strip().upper(),
        "origem": (request.args.get("origem") or "").strip().upper(),
    }

    pedidos = PedidosAdminService.listar_pedidos(filtros=filtros)
    dashboard = PedidosAdminService.montar_dashboard(pedidos)
    unidades = PedidosAdminService.listar_unidades_ativas()
    status_opcoes = PedidosAdminService.listar_status()
    origem_opcoes = PedidosAdminService.listar_origens()

    return render_template(
        "pedidos_admin/lista.html",
        pedidos=pedidos,
        dashboard=dashboard,
        unidades=unidades,
        filtros=filtros,
        status_opcoes=status_opcoes,
        origem_opcoes=origem_opcoes,
    )


@bp.get("/<pedido_id>")
@login_interno_obrigatorio
@perfil_interno_obrigatorio
def detalhe(pedido_id):
    pedido = PedidosAdminService.buscar_pedido_por_id(pedido_id)

    if not pedido:
        flash("Pedido não encontrado.", "warning")
        return redirect(url_for("pedidos_admin.lista"))

    proximos_status = []

    if not pedido.get("fechado_em_caixa"):
        proximos_status = PedidosAdminService.listar_proximos_status(pedido.get("status"))

    return render_template(
        "pedidos_admin/detalhe.html",
        pedido=pedido,
        proximos_status=proximos_status,
    )


@bp.post("/<pedido_id>/status")
@login_interno_obrigatorio
@perfil_interno_obrigatorio
def alterar_status(pedido_id):
    novo_status = (request.form.get("novo_status") or "").strip().upper()

    sucesso, mensagem, pedido = PedidosAdminService.alterar_status_pedido(
        pedido_id=pedido_id,
        novo_status=novo_status,
        usuario_nome=_usuario_nome_logado(),
    )

    flash(mensagem, "success" if sucesso else "danger")

    if pedido:
        return redirect(url_for("pedidos_admin.detalhe", pedido_id=pedido_id))

    return redirect(url_for("pedidos_admin.lista"))


@bp.post("/<pedido_id>/pagamento")
@login_interno_obrigatorio
@perfil_interno_obrigatorio
def simular_pagamento(pedido_id):
    resultado = (request.form.get("resultado_pagamento") or "").strip().upper()

    sucesso, mensagem, pedido = PedidosAdminService.simular_pagamento_pedido(
        pedido_id=pedido_id,
        resultado=resultado,
        usuario_nome=_usuario_nome_logado(),
    )

    flash(mensagem, "success" if sucesso else "danger")

    if pedido:
        return redirect(url_for("pedidos_admin.detalhe", pedido_id=pedido_id))

    return redirect(url_for("pedidos_admin.lista"))


@bp.post("/<pedido_id>/acao/pagar")
@login_interno_obrigatorio
@perfil_interno_obrigatorio
def acao_confirmar_pagamento(pedido_id):
    sucesso, mensagem, pedido = PedidosAdminService.simular_pagamento_pedido(
        pedido_id=pedido_id,
        resultado=PedidosAdminService.PAGAMENTO_PAGO,
        usuario_nome=_usuario_nome_logado(),
    )

    flash(mensagem, "success" if sucesso else "danger")
    return _voltar_para_lista()


@bp.post("/<pedido_id>/acao/preparo")
@login_interno_obrigatorio
@perfil_interno_obrigatorio
def acao_enviar_preparo(pedido_id):
    sucesso, mensagem, pedido = PedidosAdminService.alterar_status_pedido(
        pedido_id=pedido_id,
        novo_status=PedidosAdminService.STATUS_EM_PREPARO,
        usuario_nome=_usuario_nome_logado(),
    )

    flash(mensagem, "success" if sucesso else "danger")
    return _voltar_para_lista()


@bp.post("/<pedido_id>/acao/pronto")
@login_interno_obrigatorio
@perfil_interno_obrigatorio
def acao_marcar_pronto(pedido_id):
    sucesso, mensagem, pedido = PedidosAdminService.alterar_status_pedido(
        pedido_id=pedido_id,
        novo_status=PedidosAdminService.STATUS_PRONTO,
        usuario_nome=_usuario_nome_logado(),
    )

    flash(mensagem, "success" if sucesso else "danger")
    return _voltar_para_lista()


@bp.post("/<pedido_id>/acao/finalizar")
@login_interno_obrigatorio
@perfil_interno_obrigatorio
def acao_finalizar(pedido_id):
    sucesso, mensagem, pedido = PedidosAdminService.alterar_status_pedido(
        pedido_id=pedido_id,
        novo_status=PedidosAdminService.STATUS_ENTREGUE,
        usuario_nome=_usuario_nome_logado(),
    )

    flash(mensagem, "success" if sucesso else "danger")
    return _voltar_para_lista()


@bp.post("/<pedido_id>/acao/cancelar")
@login_interno_obrigatorio
@perfil_interno_obrigatorio
def acao_cancelar(pedido_id):
    sucesso, mensagem, pedido = PedidosAdminService.alterar_status_pedido(
        pedido_id=pedido_id,
        novo_status=PedidosAdminService.STATUS_CANCELADO,
        usuario_nome=_usuario_nome_logado(),
    )

    flash(mensagem, "success" if sucesso else "danger")
    return _voltar_para_lista()