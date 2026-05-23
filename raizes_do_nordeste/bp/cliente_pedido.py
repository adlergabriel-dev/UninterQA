from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from services.cliente_pedido_service import ClientePedidoService

bp = Blueprint("cliente_pedido", __name__, url_prefix="/cliente")

CHAVE_CARRINHO = "carrinho_cliente"


def login_cliente_obrigatorio(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        cliente = session.get("cliente")
        if not cliente:
            flash("Faça login para acessar a área do cliente.", "warning")
            return redirect(url_for("cliente_auth.login"))
        return view(*args, **kwargs)
    return wrapper


def _cliente_logado_validado():
    cliente_sessao = session.get("cliente") or {}
    cliente_id = cliente_sessao.get("id")

    cliente = ClientePedidoService.buscar_cliente_por_id(cliente_id)

    if not cliente:
        session.pop("cliente", None)
        return None, "Sessão inválida. Faça login novamente."

    if not cliente.get("ativo", True):
        session.pop("cliente", None)
        return None, "Seu cadastro está inativo. Entre em contato com o suporte."

    return cliente, ""


def _obter_carrinho():
    carrinho = session.get(CHAVE_CARRINHO) or {}
    return ClientePedidoService.normalizar_carrinho(carrinho)


def _salvar_carrinho(carrinho):
    session[CHAVE_CARRINHO] = ClientePedidoService.normalizar_carrinho(carrinho)
    session.modified = True


@bp.route("/pedido/novo", methods=["GET"])
@login_cliente_obrigatorio
def novo_pedido():
    cliente, erro = _cliente_logado_validado()

    if erro:
        flash(erro, "warning")
        return redirect(url_for("cliente_auth.login"))

    unidade_id = (request.args.get("unidade_id") or "").strip()

    unidades = ClientePedidoService.listar_unidades_ativas()
    produtos = ClientePedidoService.listar_itens_por_unidade(unidade_id) if unidade_id else []
    carrinho = _obter_carrinho()

    return render_template(
        "cliente/novo_pedido.html",
        cliente=cliente,
        unidades=unidades,
        produtos=produtos,
        filtros={"unidade_id": unidade_id},
        form_data={"unidade_id": unidade_id},
        carrinho=carrinho,
    )


@bp.post("/carrinho/adicionar")
@login_cliente_obrigatorio
def adicionar_carrinho():
    print("\n========== DEBUG ADICIONAR CARRINHO ==========")
    print("[FORM RECEBIDO]", dict(request.form))

    cliente, erro = _cliente_logado_validado()

    if erro:
        print("[ERRO CLIENTE]", erro)
        flash(erro, "warning")
        return redirect(url_for("cliente_auth.login"))

    unidade_id = (request.form.get("unidade_id") or "").strip()
    produto_id = (request.form.get("produto_id") or "").strip()
    observacao = (request.form.get("observacao") or "").strip()

    try:
        quantidade = int(request.form.get("quantidade") or 1)
    except Exception:
        quantidade = 1

    print("[UNIDADE_ID]", unidade_id)
    print("[PRODUTO_ID]", produto_id)
    print("[QUANTIDADE]", quantidade)
    print("[OBSERVACAO]", observacao)

    sucesso, mensagem, item = ClientePedidoService.montar_item_carrinho(
        unidade_id=unidade_id,
        produto_id=produto_id,
        quantidade=quantidade,
        observacao=observacao,
    )

    print("[SUCESSO MONTAR ITEM]", sucesso)
    print("[MENSAGEM]", mensagem)
    print("[ITEM]", item)

    if not sucesso:
        flash(mensagem, "danger")
        print("========== FIM DEBUG COM ERRO ==========\n")
        return redirect(url_for("cliente_pedido.novo_pedido", unidade_id=unidade_id))

    carrinho_atual = session.get(CHAVE_CARRINHO) or {}
    print("[CARRINHO ANTES SESSION]", carrinho_atual)

    carrinho = ClientePedidoService.normalizar_carrinho(carrinho_atual)

    if carrinho.get("itens") and carrinho.get("unidade_id") != unidade_id:
        carrinho = {}
        flash("Carrinho anterior limpo, pois a filial foi alterada.", "warning")

    carrinho = ClientePedidoService.adicionar_item_carrinho(carrinho, item)

    print("[CARRINHO DEPOIS SERVICE]", carrinho)

    session[CHAVE_CARRINHO] = carrinho
    session.modified = True

    print("[SESSION SALVA]", session.get(CHAVE_CARRINHO))
    print("========== FIM DEBUG ADICIONAR CARRINHO ==========\n")

    flash("Item adicionado ao carrinho.", "success")
    return redirect(url_for("cliente_pedido.carrinho"))


@bp.get("/carrinho")
@login_cliente_obrigatorio
def carrinho():
    cliente, erro = _cliente_logado_validado()

    if erro:
        flash(erro, "warning")
        return redirect(url_for("cliente_auth.login"))

    print("\n========== DEBUG ABRIR CARRINHO ==========")
    print("[SESSION BRUTA]", session.get(CHAVE_CARRINHO))

    carrinho = _obter_carrinho()

    print("[CARRINHO NORMALIZADO]", carrinho)
    print("========== FIM DEBUG ABRIR CARRINHO ==========\n")

    return render_template(
        "cliente/carrinho.html",
        cliente=cliente,
        carrinho=carrinho,
    )

@bp.post("/carrinho/atualizar")
@login_cliente_obrigatorio
def atualizar_carrinho():
    carrinho = _obter_carrinho()

    if not carrinho.get("itens"):
        flash("Seu carrinho está vazio.", "warning")
        return redirect(url_for("cliente_pedido.carrinho"))

    carrinho = ClientePedidoService.atualizar_carrinho_por_formulario(
        carrinho=carrinho,
        form_data=request.form,
    )

    _salvar_carrinho(carrinho)

    flash("Carrinho atualizado.", "success")
    return redirect(url_for("cliente_pedido.carrinho"))


@bp.post("/carrinho/remover/<produto_id>")
@login_cliente_obrigatorio
def remover_carrinho(produto_id):
    carrinho = _obter_carrinho()

    carrinho = ClientePedidoService.remover_item_carrinho(
        carrinho=carrinho,
        produto_id=produto_id,
    )

    _salvar_carrinho(carrinho)

    flash("Item removido do carrinho.", "success")
    return redirect(url_for("cliente_pedido.carrinho"))


@bp.post("/carrinho/limpar")
@login_cliente_obrigatorio
def limpar_carrinho():
    session.pop(CHAVE_CARRINHO, None)
    session.modified = True

    flash("Carrinho limpo com sucesso.", "success")
    return redirect(url_for("cliente_pedido.carrinho"))


@bp.post("/carrinho/finalizar")
@login_cliente_obrigatorio
def finalizar_carrinho():
    cliente, erro = _cliente_logado_validado()

    if erro:
        flash(erro, "warning")
        return redirect(url_for("cliente_auth.login"))

    carrinho = _obter_carrinho()
    pagamento_metodo = (request.form.get("pagamento_metodo") or "").strip().upper()

    sucesso, mensagem, pedido_id = ClientePedidoService.criar_pedido_por_carrinho(
        cliente_id=cliente["id"],
        carrinho=carrinho,
        pagamento_metodo=pagamento_metodo,
    )

    if not sucesso:
        flash(mensagem, "danger")
        return redirect(url_for("cliente_pedido.carrinho"))

    session.pop(CHAVE_CARRINHO, None)
    session.modified = True

    flash("Pedido realizado com sucesso.", "success")
    return redirect(url_for("cliente_pedido.meus_pedidos"))


@bp.get("/pedidos")
@login_cliente_obrigatorio
def meus_pedidos():
    cliente, erro = _cliente_logado_validado()

    if erro:
        flash(erro, "warning")
        return redirect(url_for("cliente_auth.login"))

    pedidos = ClientePedidoService.listar_pedidos_do_cliente(cliente["id"])

    return render_template(
        "cliente/meus_pedidos.html",
        cliente=cliente,
        pedidos=pedidos,
    )


@bp.get("/pedidos/<pedido_id>")
@login_cliente_obrigatorio
def detalhe_pedido(pedido_id):
    cliente_sessao = session.get("cliente") or {}
    cliente_id = cliente_sessao.get("id")

    pedido = ClientePedidoService.buscar_pedido_do_cliente(cliente_id, pedido_id)

    if not pedido:
        flash("Pedido não encontrado.", "warning")
        return redirect(url_for("cliente_pedido.meus_pedidos"))

    return render_template(
        "cliente/detalhe_pedido.html",
        pedido=pedido,
    )


@bp.post("/pedidos/<pedido_id>/cancelar")
@login_cliente_obrigatorio
def cancelar_pedido(pedido_id):
    cliente_sessao = session.get("cliente") or {}
    cliente_id = cliente_sessao.get("id")

    sucesso, mensagem, pedido = ClientePedidoService.cancelar_pedido_do_cliente(
        cliente_id=cliente_id,
        pedido_id=pedido_id,
    )

    flash(mensagem, "success" if sucesso else "danger")

    if pedido:
        return redirect(url_for("cliente_pedido.detalhe_pedido", pedido_id=pedido_id))

    return redirect(url_for("cliente_pedido.meus_pedidos"))