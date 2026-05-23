from __future__ import annotations

import json

from flask import Blueprint, render_template, request, redirect, url_for, flash

from services.pedido_totem_service import PedidoTotemService


bp = Blueprint("pedido_totem", __name__, url_prefix="/totem")

service = PedidoTotemService()


@bp.route("/")
def inicio():
    unidades = service.listar_unidades_ativas()

    return render_template(
        "pedido_totem/inicio.html",
        unidades=unidades
    )


@bp.route("/unidade/<unidade_id>")
def cardapio(unidade_id):
    unidade = service.buscar_unidade(unidade_id)

    if not unidade:
        flash("Unidade não encontrada.", "danger")
        return redirect(url_for("pedido_totem.inicio"))

    itens = service.listar_cardapio_por_unidade(unidade_id)

    return render_template(
        "pedido_totem/cardapio.html",
        unidade=unidade,
        itens=itens
    )


@bp.route("/carrinho/<unidade_id>")
def carrinho(unidade_id):
    unidade = service.buscar_unidade(unidade_id)

    if not unidade:
        flash("Unidade não encontrada.", "danger")
        return redirect(url_for("pedido_totem.inicio"))

    return render_template(
        "pedido_totem/carrinho.html",
        unidade=unidade
    )


@bp.route("/finalizar", methods=["POST"])
def finalizar():
    try:
        unidade_id = (request.form.get("unidade_id") or "").strip()
        cliente_nome = (request.form.get("cliente_nome") or "Cliente Totem").strip()
        observacao = (request.form.get("observacao") or "").strip()
        forma_pagamento = (request.form.get("forma_pagamento") or "TOTEM").strip()

        itens_json = request.form.get("itens_json") or "[]"
        itens = json.loads(itens_json)

        if not unidade_id:
            raise ValueError("Unidade não informada.")

        if not itens:
            raise ValueError("Carrinho vazio.")

        pedido = service.criar_pedido_totem(
            unidade_id=unidade_id,
            itens_carrinho=itens,
            cliente_nome=cliente_nome,
            observacao=observacao,
            forma_pagamento=forma_pagamento
        )

        return redirect(url_for(
            "pedido_totem.sucesso",
            codigo=pedido.get("codigo")
        ))

    except ValueError as e:
        flash(str(e), "danger")
        unidade_id = request.form.get("unidade_id") or ""
        if unidade_id:
            return redirect(url_for("pedido_totem.carrinho", unidade_id=unidade_id))
        return redirect(url_for("pedido_totem.inicio"))

    except Exception as e:
        flash(f"Erro ao finalizar pedido: {str(e)}", "danger")
        unidade_id = request.form.get("unidade_id") or ""
        if unidade_id:
            return redirect(url_for("pedido_totem.carrinho", unidade_id=unidade_id))
        return redirect(url_for("pedido_totem.inicio"))


@bp.route("/sucesso/<codigo>")
def sucesso(codigo):
    return render_template(
        "pedido_totem/sucesso.html",
        codigo=codigo
    )