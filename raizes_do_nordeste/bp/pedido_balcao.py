from __future__ import annotations

import json

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session

from utils.decorators import login_required, perfil_required
from services.pedido_balcao_service import PedidoBalcaoService
from services.cliente_service import ClienteService

bp = Blueprint("pedido_balcao", __name__, url_prefix="/pedido-balcao")


@bp.route("/dashboard")
@login_required
@perfil_required("ADMIN", "GERENTE", "USUARIO")
def dashboard():
    indicadores = PedidoBalcaoService.dashboard_balcao()
    return render_template("pedido_balcao/dashboard.html", indicadores=indicadores)


@bp.route("/")
@login_required
@perfil_required("ADMIN", "GERENTE", "USUARIO")
def lista():
    filtros = {
        "codigo": request.args.get("codigo", "").strip(),
        "cliente": request.args.get("cliente", "").strip(),
        "unidade": request.args.get("unidade", "").strip(),
        "status": request.args.get("status", "").strip(),
        "forma_pagamento": request.args.get("forma_pagamento", "").strip(),
        "situacao_pagamento": request.args.get("situacao_pagamento", "").strip(),
    }

    pedidos = PedidoBalcaoService.listar_pedidos_balcao(filtros)
    unidades = PedidoBalcaoService.listar_unidades_ativas()
    status_list = PedidoBalcaoService.listar_status_disponiveis()
    formas_pagamento = PedidoBalcaoService.listar_formas_pagamento()
    situacoes_pagamento = PedidoBalcaoService.listar_situacoes_pagamento()

    return render_template(
        "pedido_balcao/lista.html",
        pedidos=pedidos,
        filtros=filtros,
        unidades=unidades,
        status_list=status_list,
        formas_pagamento=formas_pagamento,
        situacoes_pagamento=situacoes_pagamento,
    )


@bp.route("/novo", methods=["GET", "POST"])
@login_required
@perfil_required("ADMIN", "GERENTE", "USUARIO")
def novo():
    unidades = PedidoBalcaoService.listar_unidades_ativas()
    clientes = PedidoBalcaoService.listar_clientes_ativos()
    formas_pagamento = PedidoBalcaoService.listar_formas_pagamento()

    if request.method == "POST":
        try:
            unidade_id = (request.form.get("unidade_id") or "").strip()
            cliente_id = (request.form.get("cliente_id") or "").strip()
            forma_pagamento = (request.form.get("forma_pagamento") or "").strip()
            observacao = (request.form.get("observacao") or "").strip()

            itens_json = request.form.get("itens_json") or "[]"
            itens = json.loads(itens_json)

            usuario = session.get("usuario", {}) or {}
            usuario_nome = usuario.get("nome", "")
            usuario_id = usuario.get("id", "")

            pedido_id = PedidoBalcaoService.criar_pedido_balcao(
                unidade_id=unidade_id,
                cliente_id=cliente_id,
                itens=itens,
                forma_pagamento=forma_pagamento,
                observacao=observacao,
                usuario_nome=usuario_nome,
                usuario_id=usuario_id
            )

            flash("Pedido de balcão criado com sucesso.", "success")
            return redirect(url_for("pedido_balcao.detalhe", pedido_id=pedido_id))

        except ValueError as e:
            flash(str(e), "danger")
        except Exception as e:
            flash(f"Erro ao criar pedido: {e}", "danger")

    return render_template(
        "pedido_balcao/form.html",
        unidades=unidades,
        clientes=clientes,
        formas_pagamento=formas_pagamento
    )


@bp.route("/editar/<pedido_id>", methods=["GET", "POST"])
@login_required
@perfil_required("ADMIN", "GERENTE", "USUARIO")
def editar(pedido_id):
    pedido = PedidoBalcaoService.buscar_pedido_por_id(pedido_id)
    if not pedido:
        flash("Pedido não encontrado.", "danger")
        return redirect(url_for("pedido_balcao.lista"))

    if not PedidoBalcaoService.pedido_permite_edicao(pedido):
        flash("Este pedido não pode mais ser editado.", "danger")
        return redirect(url_for("pedido_balcao.detalhe", pedido_id=pedido_id))

    clientes = PedidoBalcaoService.listar_clientes_ativos()
    formas_pagamento = PedidoBalcaoService.listar_formas_pagamento()

    if request.method == "POST":
        try:
            cliente_id = (request.form.get("cliente_id") or "").strip()
            forma_pagamento = (request.form.get("forma_pagamento") or "").strip()
            observacao = (request.form.get("observacao") or "").strip()

            itens_json = request.form.get("itens_json") or "[]"
            itens = json.loads(itens_json)

            usuario = session.get("usuario", {}) or {}
            usuario_nome = usuario.get("nome", "")
            usuario_id = usuario.get("id", "")

            PedidoBalcaoService.atualizar_pedido_balcao(
                pedido_id=pedido_id,
                cliente_id=cliente_id,
                itens=itens,
                forma_pagamento=forma_pagamento,
                observacao=observacao,
                usuario_nome=usuario_nome,
                usuario_id=usuario_id,
            )

            flash("Pedido atualizado com sucesso.", "success")
            return redirect(url_for("pedido_balcao.detalhe", pedido_id=pedido_id))

        except ValueError as e:
            flash(str(e), "danger")
        except Exception as e:
            flash(f"Erro ao atualizar pedido: {e}", "danger")

    return render_template(
        "pedido_balcao/editar.html",
        pedido=pedido,
        clientes=clientes,
        formas_pagamento=formas_pagamento,
    )


@bp.route("/detalhe/<pedido_id>")
@login_required
@perfil_required("ADMIN", "GERENTE", "USUARIO")
def detalhe(pedido_id):
    pedido = PedidoBalcaoService.buscar_pedido_por_id(pedido_id)
    if not pedido:
        flash("Pedido não encontrado.", "danger")
        return redirect(url_for("pedido_balcao.lista"))

    status_list = PedidoBalcaoService.listar_status_disponiveis()
    permite_edicao = PedidoBalcaoService.pedido_permite_edicao(pedido)

    return render_template(
        "pedido_balcao/detalhe.html",
        pedido=pedido,
        status_list=status_list,
        permite_edicao=permite_edicao,
    )


@bp.route("/imprimir/<pedido_id>")
@login_required
@perfil_required("ADMIN", "GERENTE", "USUARIO")
def imprimir(pedido_id):
    pedido = PedidoBalcaoService.buscar_pedido_por_id(pedido_id)
    if not pedido:
        flash("Pedido não encontrado.", "danger")
        return redirect(url_for("pedido_balcao.lista"))

    return render_template("pedido_balcao/imprimir.html", pedido=pedido)


@bp.route("/status/<pedido_id>", methods=["POST"])
@login_required
@perfil_required("ADMIN", "GERENTE", "USUARIO")
def atualizar_status(pedido_id):
    try:
        novo_status = (request.form.get("novo_status") or "").strip().upper()
        usuario = session.get("usuario", {}) or {}

        PedidoBalcaoService.atualizar_status(
            pedido_id=pedido_id,
            novo_status=novo_status,
            usuario_nome=usuario.get("nome", ""),
            usuario_id=usuario.get("id", ""),
        )

        flash("Status atualizado com sucesso.", "success")

    except ValueError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Erro ao atualizar status: {e}", "danger")

    return redirect(url_for("pedido_balcao.detalhe", pedido_id=pedido_id))


@bp.route("/pagar/<pedido_id>", methods=["POST"])
@login_required
@perfil_required("ADMIN", "GERENTE", "USUARIO")
def pagar(pedido_id):
    try:
        usuario = session.get("usuario", {}) or {}

        PedidoBalcaoService.confirmar_pagamento(
            pedido_id=pedido_id,
            usuario_nome=usuario.get("nome", ""),
            usuario_id=usuario.get("id", ""),
        )

        flash("Pagamento confirmado com sucesso.", "success")

    except ValueError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Erro ao confirmar pagamento: {e}", "danger")

    return redirect(url_for("pedido_balcao.detalhe", pedido_id=pedido_id))


@bp.route("/cancelar/<pedido_id>", methods=["POST"])
@login_required
@perfil_required("ADMIN", "GERENTE", "USUARIO")
def cancelar(pedido_id):
    try:
        usuario = session.get("usuario", {}) or {}

        PedidoBalcaoService.cancelar_pedido(
            pedido_id=pedido_id,
            usuario_nome=usuario.get("nome", ""),
            usuario_id=usuario.get("id", ""),
        )

        flash("Pedido cancelado com sucesso.", "success")

    except ValueError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Erro ao cancelar pedido: {e}", "danger")

    return redirect(url_for("pedido_balcao.detalhe", pedido_id=pedido_id))


@bp.route("/api/cardapio/<unidade_id>")
@login_required
@perfil_required("ADMIN", "GERENTE", "USUARIO")
def api_cardapio_por_unidade(unidade_id):
    itens = PedidoBalcaoService.listar_cardapio_por_unidade(unidade_id)

    retorno = []
    for item in itens:
        retorno.append({
            "id": item.get("id"),
            "produto_id": item.get("produto_id", ""),
            "nome": item.get("nome_produto", ""),
            "descricao": "",
            "valor": float(item.get("preco_venda", 0) or 0),
            "categoria": "",
            "unidade_id": item.get("unidade_id", ""),
            "unidade_nome": item.get("nome_unidade", "")
        })

    return jsonify(retorno)


@bp.route("/api/clientes/novo", methods=["POST"])
@login_required
@perfil_required("ADMIN", "GERENTE", "USUARIO")
def api_novo_cliente():
    try:
        nome = (request.form.get("nome") or "").strip()
        telefone = (request.form.get("telefone") or "").strip()
        email = (request.form.get("email") or "").strip()
        cpf = (request.form.get("cpf") or "").strip()

        if not nome:
            return jsonify({"ok": False, "mensagem": "Informe o nome do cliente."}), 400

        if not telefone:
            return jsonify({"ok": False, "mensagem": "Informe o telefone do cliente."}), 400

        cliente_existente = ClienteService.buscar_por_telefone(telefone)
        if cliente_existente:
            return jsonify({
                "ok": True,
                "mensagem": "Cliente já existente localizado pelo telefone.",
                "cliente": {
                    "id": cliente_existente.get("id"),
                    "nome": cliente_existente.get("nome", ""),
                    "telefone": cliente_existente.get("telefone", ""),
                    "email": cliente_existente.get("email", ""),
                    "cpf": cliente_existente.get("cpf", ""),
                }
            })

        cliente_id = ClienteService.criar({
            "nome": nome,
            "telefone": telefone,
            "email": email,
            "cpf": cpf,
        })

        cliente = ClienteService.buscar_por_id(cliente_id)

        return jsonify({
            "ok": True,
            "mensagem": "Cliente cadastrado com sucesso.",
            "cliente": {
                "id": cliente.get("id"),
                "nome": cliente.get("nome", ""),
                "telefone": cliente.get("telefone", ""),
                "email": cliente.get("email", ""),
                "cpf": cliente.get("cpf", ""),
            }
        })

    except Exception as e:
        return jsonify({"ok": False, "mensagem": f"Erro ao cadastrar cliente: {e}"}), 500