from flask import Blueprint, render_template, request, redirect, url_for, flash

from utils.decorators import login_required, perfil_required
from services.pedido_service import PedidoService
from services.cliente_service import ClienteService
from services.unidade_service import UnidadeService
from services.produto_service import ProdutoService

bp = Blueprint("pedidos", __name__, url_prefix="/pedidos")


@bp.route("/")
@login_required
@perfil_required("ADMIN", "GERENTE", "USUARIO")
def lista():
    pedidos = PedidoService.listar()

    filtro_codigo = request.args.get("codigo", "").strip().upper()
    filtro_cliente = request.args.get("cliente", "").strip().lower()
    filtro_unidade = request.args.get("unidade", "").strip().lower()
    filtro_status = request.args.get("status", "").strip().upper()
    filtro_pagamento = request.args.get("pagamento", "").strip().upper()

    if filtro_codigo:
        pedidos = [
            p for p in pedidos
            if filtro_codigo in (p.get("codigo_pedido", "") or "").upper()
        ]

    if filtro_cliente:
        pedidos = [
            p for p in pedidos
            if filtro_cliente in (p.get("cliente_nome", "") or "").lower()
        ]

    if filtro_unidade:
        pedidos = [
            p for p in pedidos
            if filtro_unidade in (p.get("unidade_nome", "") or "").lower()
        ]

    if filtro_status:
        pedidos = [
            p for p in pedidos
            if (p.get("status", "") or "").upper() == filtro_status
        ]

    if filtro_pagamento:
        pedidos = [
            p for p in pedidos
            if (p.get("pagamento_status", "") or "").upper() == filtro_pagamento
        ]

    filtros = {
        "codigo": request.args.get("codigo", "").strip(),
        "cliente": request.args.get("cliente", "").strip(),
        "unidade": request.args.get("unidade", "").strip(),
        "status": request.args.get("status", "").strip(),
        "pagamento": request.args.get("pagamento", "").strip(),
    }

    return render_template("pedidos/lista.html", pedidos=pedidos, filtros=filtros)


@bp.route("/novo", methods=["GET", "POST"])
@login_required
@perfil_required("ADMIN", "GERENTE", "USUARIO")
def novo():
    clientes = ClienteService.listar()
    unidades = UnidadeService.listar()
    produtos = ProdutoService.listar()

    if request.method == "POST":
        try:
            cliente_id = request.form.get("cliente_id", "").strip()
            unidade_id = request.form.get("unidade_id", "").strip()
            produto_id = request.form.get("produto_id", "").strip()
            quantidade = request.form.get("quantidade", "").strip()

            if not cliente_id:
                flash("O cliente é obrigatório.", "warning")
                return render_template(
                    "pedidos/form.html",
                    pedido=request.form,
                    clientes=clientes,
                    unidades=unidades,
                    produtos=produtos,
                )

            if not unidade_id:
                flash("A unidade é obrigatória.", "warning")
                return render_template(
                    "pedidos/form.html",
                    pedido=request.form,
                    clientes=clientes,
                    unidades=unidades,
                    produtos=produtos,
                )

            if not produto_id:
                flash("O produto é obrigatório.", "warning")
                return render_template(
                    "pedidos/form.html",
                    pedido=request.form,
                    clientes=clientes,
                    unidades=unidades,
                    produtos=produtos,
                )

            if not quantidade:
                flash("A quantidade é obrigatória.", "warning")
                return render_template(
                    "pedidos/form.html",
                    pedido=request.form,
                    clientes=clientes,
                    unidades=unidades,
                    produtos=produtos,
                )

            pedido_id = PedidoService.criar_pedido_simples(request.form)
            flash("Pedido criado com sucesso.", "success")
            return redirect(url_for("pedidos.detalhe", pedido_id=pedido_id))

        except ValueError as e:
            flash(str(e), "warning")
        except Exception:
            flash("Erro ao criar pedido.", "danger")

    return render_template(
        "pedidos/form.html",
        pedido=None,
        clientes=clientes,
        unidades=unidades,
        produtos=produtos,
    )


@bp.route("/<pedido_id>")
@login_required
@perfil_required("ADMIN", "GERENTE", "USUARIO")
def detalhe(pedido_id):
    pedido = PedidoService.buscar_por_id(pedido_id)

    if not pedido:
        flash("Pedido não encontrado.", "danger")
        return redirect(url_for("pedidos.lista"))

    itens = PedidoService.listar_itens(pedido_id)
    historico = PedidoService.listar_historico_status(pedido_id)
    proximos_status = PedidoService.listar_proximos_status(pedido.get("status", ""))
    pagamentos = PedidoService.listar_pagamentos(pedido_id)

    return render_template(
        "pedidos/detalhe.html",
        pedido=pedido,
        itens=itens,
        historico=historico,
        proximos_status=proximos_status,
        pagamentos=pagamentos,
    )


@bp.route("/<pedido_id>/alterar-status", methods=["POST"])
@login_required
@perfil_required("ADMIN", "GERENTE")
def alterar_status(pedido_id):
    novo_status = request.form.get("novo_status", "").strip()
    observacao = request.form.get("observacao_status", "").strip()

    try:
        if not novo_status:
            flash("Selecione um novo status.", "warning")
            return redirect(url_for("pedidos.detalhe", pedido_id=pedido_id))

        PedidoService.alterar_status(pedido_id, novo_status, observacao)
        flash("Status do pedido alterado com sucesso.", "success")

    except ValueError as e:
        flash(str(e), "warning")
    except Exception:
        flash("Erro ao alterar status do pedido.", "danger")

    return redirect(url_for("pedidos.detalhe", pedido_id=pedido_id))


@bp.route("/<pedido_id>/simular-pagamento", methods=["POST"])
@login_required
@perfil_required("ADMIN", "GERENTE")
def simular_pagamento(pedido_id):
    resultado = request.form.get("resultado_pagamento", "").strip()

    try:
        if not resultado:
            flash("Selecione um resultado de pagamento.", "warning")
            return redirect(url_for("pedidos.detalhe", pedido_id=pedido_id))

        PedidoService.simular_pagamento(pedido_id, resultado)
        flash("Pagamento simulado com sucesso.", "success")

    except ValueError as e:
        flash(str(e), "warning")
    except Exception:
        flash("Erro ao simular pagamento.", "danger")

    return redirect(url_for("pedidos.detalhe", pedido_id=pedido_id))