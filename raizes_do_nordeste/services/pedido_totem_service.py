from datetime import datetime
from typing import Dict, List, Any, Optional

from services.firebase_service import FirebaseService


class PedidoTotemService:
    def __init__(self):
        self.firebase = FirebaseService()

    def _to_float(self, valor) -> float:
        try:
            if isinstance(valor, str):
                valor = (
                    valor
                    .replace("R$", "")
                    .replace(".", "")
                    .replace(",", ".")
                    .strip()
                )
            return float(valor or 0)
        except Exception:
            return 0.0

    def _formatar_moeda(self, valor) -> str:
        try:
            return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return "R$ 0,00"

    def _pegar_valor(self, item: dict, produto: dict = None) -> float:
        produto = produto or {}

        campos_possiveis = [
            item.get("valor"),
            item.get("preco"),
            item.get("preco_venda"),
            item.get("valor_venda"),
            item.get("valor_unitario"),
            item.get("preco_unitario"),

            produto.get("valor"),
            produto.get("preco"),
            produto.get("preco_venda"),
            produto.get("valor_venda"),
            produto.get("valor_unitario"),
            produto.get("preco_unitario"),
        ]

        for valor in campos_possiveis:
            valor_float = self._to_float(valor)

            if valor_float > 0:
                return valor_float

        return 0.0

    def gerar_codigo(self) -> str:
        return "TOT" + datetime.now().strftime("%Y%m%d%H%M%S")

    def listar_unidades_ativas(self) -> List[Dict[str, Any]]:
        unidades = self.firebase.listar_documentos("unidades")

        resultado = []
        for unidade in unidades:
            ativo = unidade.get("ativo", True)

            if ativo is True:
                resultado.append(unidade)
                continue

            if str(ativo).strip().upper() in ["TRUE", "1", "SIM", "ATIVO"]:
                resultado.append(unidade)

        resultado.sort(key=lambda x: (x.get("nome") or x.get("unidade_nome") or "").lower())
        return resultado

    def listar_cardapio_por_unidade(self, unidade_id: str) -> List[Dict[str, Any]]:
        cardapios = self.firebase.listar_documentos("cardapio_unidade")

        resultado = []

        for item in cardapios:
            if str(item.get("unidade_id")) != str(unidade_id):
                continue

            ativo = item.get("ativo", True)
            disponivel = item.get("disponivel", True)

            if ativo is not True and str(ativo).strip().upper() not in ["TRUE", "1", "SIM", "ATIVO"]:
                continue

            if disponivel is not True and str(disponivel).strip().upper() not in ["TRUE", "1", "SIM", "DISPONIVEL"]:
                continue

            produto_id = item.get("produto_id")
            produto = {}

            if produto_id:
                produto = self.firebase.buscar_documento_por_id("produtos", produto_id) or {}

            nome_produto = (
                item.get("nome_produto")
                or item.get("produto_nome")
                or item.get("nome")
                or produto.get("nome")
                or produto.get("produto_nome")
                or produto.get("descricao")
                or "Produto sem nome"
            )

            descricao = (
                item.get("descricao")
                or item.get("descricao_produto")
                or produto.get("descricao")
                or ""
            )

            imagem_url = (
                item.get("imagem_url")
                or item.get("imagem")
                or item.get("foto")
                or produto.get("imagem_url")
                or produto.get("imagem")
                or produto.get("foto")
                or ""
            )

            valor = self._pegar_valor(item, produto)

            item["nome_produto"] = nome_produto
            item["produto_nome"] = nome_produto
            item["nome"] = nome_produto
            item["descricao"] = descricao
            item["imagem_url"] = imagem_url
            item["valor"] = valor
            item["preco_venda"] = valor

            resultado.append(item)

        resultado.sort(
            key=lambda x: (
                x.get("ordem_exibicao", 9999),
                (x.get("nome_produto") or x.get("produto_nome") or "").lower()
            )
        )

        return resultado

    def buscar_unidade(self, unidade_id: str) -> Optional[Dict[str, Any]]:
        if not unidade_id:
            return None

        return self.firebase.buscar_documento_por_id("unidades", unidade_id)

    def buscar_produto_cardapio(self, cardapio_id: str) -> Optional[Dict[str, Any]]:
        if not cardapio_id:
            return None

        item = self.firebase.buscar_documento_por_id("cardapio_unidade", cardapio_id)

        if not item:
            return None

        produto_id = item.get("produto_id")
        produto = {}

        if produto_id:
            produto = self.firebase.buscar_documento_por_id("produtos", produto_id) or {}

        nome_produto = (
            item.get("nome_produto")
            or item.get("produto_nome")
            or item.get("nome")
            or produto.get("nome")
            or produto.get("produto_nome")
            or produto.get("descricao")
            or "Produto sem nome"
        )

        descricao = (
            item.get("descricao")
            or item.get("descricao_produto")
            or produto.get("descricao")
            or ""
        )

        imagem_url = (
            item.get("imagem_url")
            or item.get("imagem")
            or item.get("foto")
            or produto.get("imagem_url")
            or produto.get("imagem")
            or produto.get("foto")
            or ""
        )

        valor = self._pegar_valor(item, produto)

        item["nome_produto"] = nome_produto
        item["produto_nome"] = nome_produto
        item["nome"] = nome_produto
        item["descricao"] = descricao
        item["imagem_url"] = imagem_url
        item["valor"] = valor
        item["preco_venda"] = valor

        return item

    def criar_pedido_totem(
        self,
        unidade_id: str,
        itens_carrinho: list,
        cliente_nome: str = "Cliente Totem",
        observacao: str = "",
        forma_pagamento: str = "TOTEM"
    ):
        if not unidade_id:
            raise ValueError("Unidade não informada.")

        if not itens_carrinho:
            raise ValueError("Carrinho vazio.")

        unidade = self.buscar_unidade(unidade_id)

        if not unidade:
            raise ValueError("Unidade não encontrada.")

        itens_pedido = []
        valor_total = 0.0
        quantidade_total = 0

        for item in itens_carrinho:
            try:
                quantidade = int(float(item.get("quantidade", 0) or 0))
            except Exception:
                quantidade = 0

            if quantidade <= 0:
                continue

            valor_unitario = self._to_float(
                item.get("valor_unitario")
                or item.get("preco_unitario")
                or item.get("preco")
                or item.get("valor")
                or item.get("preco_venda")
            )

            produto_nome = (
                item.get("produto_nome")
                or item.get("nome")
                or item.get("nome_produto")
                or "Produto sem nome"
            )

            cardapio_id = item.get("cardapio_id") or item.get("id") or ""
            produto_id = item.get("produto_id") or ""

            valor_item = round(valor_unitario * quantidade, 2)

            itens_pedido.append({
                "cardapio_id": cardapio_id,
                "produto_id": produto_id,

                "nome": produto_nome,
                "produto_nome": produto_nome,
                "nome_produto": produto_nome,
                "nome_produto_snapshot": produto_nome,

                "quantidade": quantidade,

                "valor_unitario": round(valor_unitario, 2),
                "preco_unitario": round(valor_unitario, 2),
                "preco": round(valor_unitario, 2),
                "preco_venda": round(valor_unitario, 2),

                "valor_total": valor_item,
                "subtotal": valor_item,

                "imagem_url": item.get("imagem_url", ""),
                "imagem_url_snapshot": item.get("imagem_url", ""),
                "observacao": item.get("observacao", ""),

                "snapshot_produto": {
                    "nome": produto_nome,
                    "preco": round(valor_unitario, 2),
                    "preco_formatado": self._formatar_moeda(valor_unitario),
                    "imagem_url": item.get("imagem_url", ""),
                    "cardapio_id": cardapio_id,
                    "produto_id": produto_id,
                }
            })

            valor_total += valor_item
            quantidade_total += quantidade

        if not itens_pedido:
            raise ValueError("Nenhum item válido no carrinho.")

        valor_total = round(valor_total, 2)

        agora = datetime.now()
        codigo = self.gerar_codigo()

        forma_pagamento_upper = str(forma_pagamento or "TOTEM").strip().upper()

        if forma_pagamento_upper == "DINHEIRO":
            situacao_pagamento = "PENDENTE"
            pagamento_status = "PENDENTE"
            pagamento_descricao = "Pendente"
        else:
            situacao_pagamento = "PAGO"
            pagamento_status = "PAGO"
            pagamento_descricao = "Pago"

        unidade_nome = (
            unidade.get("nome")
            or unidade.get("unidade_nome")
            or unidade.get("nome_unidade")
            or ""
        )

        pedido = {
            "codigo": codigo,
            "codigo_pedido": codigo,

            "origem": "TOTEM",
            "tipo": "TOTEM",
            "canal": "TOTEM",
            "canal_origem": "TOTEM",

            "status": "NOVO",

            "situacao_pagamento": situacao_pagamento,
            "pagamento_status": pagamento_status,
            "pagamento_status_descricao": pagamento_descricao,

            "unidade_id": unidade_id,
            "unidade_nome": unidade_nome,

            "cliente_id": "",
            "cliente_nome": cliente_nome or "Cliente Totem",
            "cliente_email": "",
            "cliente_telefone": "",

            "itens": itens_pedido,

            "quantidade_itens": len(itens_pedido),
            "quantidade_total": quantidade_total,
            "quantidade_total_itens": quantidade_total,

            "subtotal": valor_total,
            "total": valor_total,

            "valor_subtotal": valor_total,
            "valor_produtos": valor_total,
            "valor_desconto": 0.0,
            "valor_entrega": 0.0,
            "valor_total": valor_total,
            "valor_total_formatado": self._formatar_moeda(valor_total),

            "forma_pagamento": forma_pagamento_upper,
            "pagamento_metodo": forma_pagamento_upper,
            "pagamento_metodo_descricao": forma_pagamento_upper,
            "pagamento_valor": valor_total,
            "pagamento_valor_formatado": self._formatar_moeda(valor_total),
            "pagamento_transacao_id": "TOT-" + agora.strftime("%Y%m%d%H%M%S"),

            "observacao": observacao or "",

            "ativo": True,

            "criado_em": agora.isoformat(),
            "criado_em_texto": agora.strftime("%d/%m/%Y %H:%M:%S"),
            "criado_em_ord": agora.strftime("%Y-%m-%d %H:%M:%S"),

            "atualizado_em": agora.isoformat(),
            "atualizado_em_texto": agora.strftime("%d/%m/%Y %H:%M:%S"),
        }

        pedido_id = self.firebase.criar_documento("pedidos", pedido)

        pedido_ref = self.firebase.get_collection("pedidos").document(pedido_id)

        for item in itens_pedido:
            pedido_ref.collection("itens").document().set({
                "cardapio_id": item.get("cardapio_id", ""),
                "produto_id": item.get("produto_id", ""),

                "nome": item.get("produto_nome", ""),
                "produto_nome": item.get("produto_nome", ""),
                "nome_produto": item.get("produto_nome", ""),
                "nome_produto_snapshot": item.get("produto_nome", ""),

                "imagem_url": item.get("imagem_url", ""),
                "imagem_url_snapshot": item.get("imagem_url", ""),

                "preco_unitario": item.get("valor_unitario", 0),
                "valor_unitario": item.get("valor_unitario", 0),

                "quantidade": item.get("quantidade", 0),

                "subtotal": item.get("valor_total", 0),
                "valor_total": item.get("valor_total", 0),
            })

        pedido_ref.collection("pagamentos").document().set({
            "metodo": forma_pagamento_upper,
            "status": pagamento_status,
            "valor": valor_total,
            "valor_formatado": self._formatar_moeda(valor_total),
            "simulado": True,
            "resultado_simulado": pagamento_status,
            "transacao_id": "TOT-" + agora.strftime("%Y%m%d%H%M%S"),
            "criado_em": agora.isoformat(),
            "atualizado_em": agora.isoformat(),
        })

        pedido_ref.collection("historico_status").document().set({
            "status_anterior": "",
            "status_novo": "NOVO",
            "origem": "TOTEM",
            "observacao": "Pedido Totem criado",
            "data_evento": agora.isoformat(),
        })

        pedido["id"] = pedido_id

        return pedido