from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any, Optional

from services.firebase_service import FirebaseService
from services.unidade_service import UnidadeService
from services.cliente_service import ClienteService


class PedidoBalcaoService:
    COLECAO_CARDAPIO = "cardapio_unidade"
    COLECAO_PRODUTOS = "produtos"
    COLECAO_PEDIDOS = "pedidos"

    ORIGEM_BALCAO = "BALCAO"

    STATUS_CRIADO = "CRIADO"
    STATUS_EM_PREPARO = "EM_PREPARO"
    STATUS_PRONTO = "PRONTO"
    STATUS_FINALIZADO = "FINALIZADO"
    STATUS_CANCELADO = "CANCELADO"

    STATUS_VALIDOS = [
        STATUS_CRIADO,
        STATUS_EM_PREPARO,
        STATUS_PRONTO,
        STATUS_FINALIZADO,
        STATUS_CANCELADO,
    ]

    STATUS_PERMITEM_EDICAO = [
        STATUS_CRIADO,
        STATUS_EM_PREPARO,
    ]

    PAGAMENTO_PENDENTE = "PENDENTE"
    PAGAMENTO_PAGO = "PAGO"

    SITUACOES_PAGAMENTO = [
        PAGAMENTO_PENDENTE,
        PAGAMENTO_PAGO,
    ]

    @classmethod
    def _agora(cls) -> datetime:
        return datetime.now()

    @classmethod
    def _agora_texto(cls) -> str:
        return cls._agora().strftime("%d/%m/%Y %H:%M:%S")

    @classmethod
    def _hoje_str(cls) -> str:
        return cls._agora().strftime("%Y-%m-%d")

    @classmethod
    def _normalizar_upper(cls, valor: Any) -> str:
        return str(valor or "").strip().upper()

    @classmethod
    def _texto(cls, valor: Any) -> str:
        return str(valor or "").strip()

    @classmethod
    def _to_float(cls, valor: Any) -> float:
        try:
            if isinstance(valor, str):
                valor = valor.replace("R$", "").replace(".", "").replace(",", ".").strip()
            return float(valor or 0)
        except Exception:
            return 0.0

    @classmethod
    def _to_int(cls, valor: Any) -> int:
        try:
            return int(float(valor or 0))
        except Exception:
            return 0

    @classmethod
    def _formatar_moeda(cls, valor):
        try:
            return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return "R$ 0,00"

    @classmethod
    def _eh_origem_balcao(cls, pedido: Dict[str, Any]) -> bool:
        origem = cls._normalizar_upper(
            pedido.get("origem")
            or pedido.get("tipo")
            or pedido.get("canal")
            or ""
        )

        return origem in ["BALCAO", "PEDIDO_BALCAO"]

    @classmethod
    def listar_status_disponiveis(cls) -> List[str]:
        return cls.STATUS_VALIDOS.copy()

    @classmethod
    def listar_formas_pagamento(cls) -> List[str]:
        return [
            "DINHEIRO",
            "PIX",
            "CARTAO_CREDITO",
            "CARTAO_DEBITO",
        ]

    @classmethod
    def listar_situacoes_pagamento(cls) -> List[str]:
        return cls.SITUACOES_PAGAMENTO.copy()

    @classmethod
    def listar_unidades_ativas(cls) -> List[Dict[str, Any]]:
        unidades = UnidadeService.listar()
        unidades = [u for u in unidades if u.get("ativo", True)]
        unidades.sort(key=lambda x: (x.get("nome") or "").lower())
        return unidades

    @classmethod
    def listar_clientes_ativos(cls) -> List[Dict[str, Any]]:
        clientes = ClienteService.listar()
        clientes = [c for c in clientes if c.get("ativo", True)]
        clientes.sort(key=lambda x: (x.get("nome") or "").lower())
        return clientes

    @classmethod
    def buscar_cliente_por_id(cls, cliente_id: str) -> Optional[Dict[str, Any]]:
        if not cliente_id:
            return None
        return ClienteService.buscar_por_id(cliente_id)

    @classmethod
    def buscar_unidade_por_id(cls, unidade_id: str) -> Optional[Dict[str, Any]]:
        if not unidade_id:
            return None
        return UnidadeService.buscar_por_id(unidade_id)

    @classmethod
    def listar_cardapio_por_unidade(cls, unidade_id: str) -> List[Dict[str, Any]]:
        if not unidade_id:
            return []

        docs = (
            FirebaseService.get_collection(cls.COLECAO_CARDAPIO)
            .where("unidade_id", "==", unidade_id)
            .where("ativo", "==", True)
            .where("disponivel", "==", True)
            .stream()
        )

        itens = []
        for doc in docs:
            item = doc.to_dict() or {}
            item["id"] = doc.id
            itens.append(item)

        itens.sort(
            key=lambda x: (
                x.get("ordem_exibicao", 9999),
                (x.get("nome_produto") or "").lower()
            )
        )
        return itens

    @classmethod
    def listar_pedidos_balcao(cls, filtros: dict | None = None) -> List[Dict[str, Any]]:
        filtros = filtros or {}
        docs = FirebaseService.get_collection(cls.COLECAO_PEDIDOS).stream()
        pedidos = []

        filtro_codigo = (filtros.get("codigo") or "").strip().lower()
        filtro_cliente = (filtros.get("cliente") or "").strip().lower()
        filtro_unidade = (filtros.get("unidade") or "").strip()
        filtro_status = (filtros.get("status") or "").strip().upper()
        filtro_pagamento = (filtros.get("forma_pagamento") or "").strip().upper()
        filtro_situacao_pagamento = (filtros.get("situacao_pagamento") or "").strip().upper()

        for doc in docs:
            item = doc.to_dict() or {}

            if not cls._eh_origem_balcao(item):
                continue

            item["id"] = doc.id

            if filtro_codigo and filtro_codigo not in (item.get("codigo_pedido", "") or "").lower():
                continue

            if filtro_cliente and filtro_cliente not in (item.get("cliente_nome", "") or "").lower():
                continue

            if filtro_unidade and filtro_unidade != (item.get("unidade_id", "") or ""):
                continue

            if filtro_status and filtro_status != (item.get("status", "") or "").upper():
                continue

            if filtro_pagamento and filtro_pagamento != (item.get("forma_pagamento", "") or "").upper():
                continue

            if filtro_situacao_pagamento and filtro_situacao_pagamento != (item.get("situacao_pagamento", "") or "").upper():
                continue

            pedidos.append(item)

        pedidos.sort(
            key=lambda x: (x.get("criado_em_ord") or "", x.get("codigo_pedido") or ""),
            reverse=True
        )
        return pedidos

    @classmethod
    def listar_pedidos_balcao_do_dia(cls) -> List[Dict[str, Any]]:
        hoje = cls._hoje_str()
        todos = cls.listar_pedidos_balcao()
        return [p for p in todos if (p.get("criado_em_ord") or "").startswith(hoje)]

    @classmethod
    def dashboard_balcao(cls) -> Dict[str, Any]:
        pedidos = cls.listar_pedidos_balcao_do_dia()

        total_vendido = 0.0
        total_pago = 0.0
        total_pendente = 0.0

        contadores_status = {
            cls.STATUS_CRIADO: 0,
            cls.STATUS_EM_PREPARO: 0,
            cls.STATUS_PRONTO: 0,
            cls.STATUS_FINALIZADO: 0,
            cls.STATUS_CANCELADO: 0,
        }

        for pedido in pedidos:
            total = float(pedido.get("total") or pedido.get("valor_total") or 0)
            status = (pedido.get("status") or "").upper()
            situacao_pagamento = (pedido.get("situacao_pagamento") or cls.PAGAMENTO_PENDENTE).upper()

            if status in contadores_status:
                contadores_status[status] += 1

            if status != cls.STATUS_CANCELADO:
                total_vendido += total

                if situacao_pagamento == cls.PAGAMENTO_PAGO:
                    total_pago += total
                else:
                    total_pendente += total

        ultimos_pedidos = pedidos[:10]

        return {
            "data_referencia": cls._agora().strftime("%d/%m/%Y"),
            "quantidade_pedidos_dia": len(pedidos),
            "total_vendido_dia": round(total_vendido, 2),
            "total_pago_dia": round(total_pago, 2),
            "total_pendente_dia": round(total_pendente, 2),
            "status_criado": contadores_status[cls.STATUS_CRIADO],
            "status_em_preparo": contadores_status[cls.STATUS_EM_PREPARO],
            "status_pronto": contadores_status[cls.STATUS_PRONTO],
            "status_finalizado": contadores_status[cls.STATUS_FINALIZADO],
            "status_cancelado": contadores_status[cls.STATUS_CANCELADO],
            "ultimos_pedidos": ultimos_pedidos,
        }

    @classmethod
    def gerar_codigo_pedido(cls) -> str:
        agora = cls._agora()
        return f"BAL{agora.strftime('%Y%m%d%H%M%S')}"

    @classmethod
    def calcular_totais(cls, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
        subtotal = 0.0
        quantidade_total = 0

        for item in itens:
            qtd = cls._to_int(item.get("quantidade"))
            valor_unitario = cls._to_float(
                item.get("valor_unitario")
                or item.get("preco_unitario")
                or item.get("preco")
            )

            subtotal += qtd * valor_unitario
            quantidade_total += qtd

        return {
            "quantidade_total": quantidade_total,
            "subtotal": round(subtotal, 2),
            "total": round(subtotal, 2),
        }

    @classmethod
    def _buscar_cardapio_por_id(cls, cardapio_id: str) -> Dict[str, Any]:
        cardapio_id = cls._texto(cardapio_id)

        if not cardapio_id:
            return {}

        doc = FirebaseService.get_collection(cls.COLECAO_CARDAPIO).document(cardapio_id).get()

        if not doc.exists:
            return {}

        data = doc.to_dict() or {}
        data["id"] = doc.id
        return data

    @classmethod
    def _buscar_produto_por_id(cls, produto_id: str) -> Dict[str, Any]:
        produto_id = cls._texto(produto_id)

        if not produto_id:
            return {}

        doc = FirebaseService.get_collection(cls.COLECAO_PRODUTOS).document(produto_id).get()

        if not doc.exists:
            return {}

        data = doc.to_dict() or {}
        data["id"] = doc.id
        return data

    @classmethod
    def _buscar_cardapio_por_produto_unidade(cls, produto_id: str, unidade_id: str = "") -> Dict[str, Any]:
        produto_id = cls._texto(produto_id)
        unidade_id = cls._texto(unidade_id)

        if not produto_id:
            return {}

        query = FirebaseService.get_collection(cls.COLECAO_CARDAPIO).where("produto_id", "==", produto_id)

        if unidade_id:
            query = query.where("unidade_id", "==", unidade_id)

        docs = query.stream()

        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            return data

        return {}

    @classmethod
    def _completar_dados_produto_item(cls, item: Dict[str, Any]) -> Dict[str, Any]:
        item = item or {}

        cardapio_id = cls._texto(
            item.get("cardapio_id")
            or item.get("id")
        )

        produto_id = cls._texto(
            item.get("produto_id")
            or item.get("id_produto")
        )

        unidade_id = cls._texto(item.get("unidade_id"))

        cardapio = cls._buscar_cardapio_por_id(cardapio_id)

        if not cardapio and produto_id:
            cardapio = cls._buscar_cardapio_por_produto_unidade(produto_id, unidade_id)

        if cardapio:
            cardapio_id = cls._texto(cardapio.get("id") or cardapio_id)
            produto_id = cls._texto(cardapio.get("produto_id") or produto_id)

        produto = cls._buscar_produto_por_id(produto_id)

        nome = cls._texto(
            item.get("produto_nome")
            or item.get("nome_produto")
            or item.get("nome")
            or cardapio.get("nome_produto")
            or produto.get("nome")
            or item.get("descricao")
        )

        descricao = cls._texto(
            item.get("produto_descricao")
            or item.get("descricao_produto")
            or item.get("descricao")
            or cardapio.get("descricao_produto")
            or produto.get("descricao")
        )

        imagem_url = cls._texto(
            item.get("imagem_url")
            or cardapio.get("imagem_url")
            or cardapio.get("imagem")
            or produto.get("imagem_url")
            or produto.get("imagem")
        )

        preco = (
            item.get("valor_unitario")
            or item.get("preco_unitario")
            or item.get("preco")
            or item.get("valor")
            or cardapio.get("preco_venda")
            or cardapio.get("preco")
            or produto.get("preco")
            or 0
        )

        return {
            "cardapio_id": cardapio_id,
            "produto_id": produto_id,
            "nome": nome,
            "produto_nome": nome,
            "descricao": descricao,
            "produto_descricao": descricao,
            "imagem_url": imagem_url,
            "preco": cls._to_float(preco),
            "unidade_id": cls._texto(item.get("unidade_id") or cardapio.get("unidade_id")),
            "unidade_nome": cls._texto(item.get("unidade_nome") or cardapio.get("nome_unidade")),
        }

    @classmethod
    def _processar_itens(cls, itens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        itens_processados = []

        for item in itens:
            quantidade = cls._to_int(item.get("quantidade"))

            if quantidade <= 0:
                continue

            dados_produto = cls._completar_dados_produto_item(item)

            nome = dados_produto.get("nome") or ""
            descricao = dados_produto.get("descricao") or ""
            cardapio_id = dados_produto.get("cardapio_id") or ""
            produto_id = dados_produto.get("produto_id") or ""

            valor_unitario = cls._to_float(
                item.get("valor_unitario")
                or item.get("preco_unitario")
                or item.get("preco")
                or item.get("valor")
                or dados_produto.get("preco")
            )

            valor_total = round(quantidade * valor_unitario, 2)

            if not nome:
                raise ValueError("Um item do pedido está sem nome. Recarregue a página e selecione o produto novamente.")

            itens_processados.append({
                "cardapio_id": cardapio_id,
                "produto_id": produto_id,

                "nome": nome,
                "produto_nome": nome,
                "descricao": descricao,
                "produto_descricao": descricao,
                "imagem_url": dados_produto.get("imagem_url", ""),

                "quantidade": quantidade,

                "valor_unitario": round(valor_unitario, 2),
                "preco_unitario": round(valor_unitario, 2),
                "preco_unitario_formatado": cls._formatar_moeda(valor_unitario),

                "valor_total": valor_total,
                "subtotal": valor_total,
                "subtotal_formatado": cls._formatar_moeda(valor_total),

                "observacao": cls._texto(item.get("observacao")),

                "snapshot_produto": {
                    "nome": nome,
                    "descricao": descricao,
                    "imagem_url": dados_produto.get("imagem_url", ""),
                    "preco": round(valor_unitario, 2),
                    "preco_formatado": cls._formatar_moeda(valor_unitario),
                    "unidade_id": dados_produto.get("unidade_id", ""),
                    "unidade_nome": dados_produto.get("unidade_nome", ""),
                    "cardapio_id": cardapio_id,
                },
            })

        if not itens_processados:
            raise ValueError("Adicione ao menos um item válido ao pedido.")

        return itens_processados

    @classmethod
    def criar_pedido_balcao(
        cls,
        unidade_id: str,
        cliente_id: str,
        itens: List[Dict[str, Any]],
        forma_pagamento: str,
        observacao: str = "",
        usuario_nome: str = "",
        usuario_id: str = ""
    ) -> str:
        if not unidade_id:
            raise ValueError("Selecione a filial.")

        if not cliente_id:
            raise ValueError("Selecione o cliente.")

        if not itens:
            raise ValueError("Adicione ao menos um item ao pedido.")

        if not forma_pagamento:
            raise ValueError("Selecione a forma de pagamento.")

        unidade = cls.buscar_unidade_por_id(unidade_id)
        if not unidade:
            raise ValueError("Filial não encontrada.")

        cliente = cls.buscar_cliente_por_id(cliente_id)
        if not cliente:
            raise ValueError("Cliente não encontrado.")

        itens_processados = cls._processar_itens(itens)
        totais = cls.calcular_totais(itens_processados)
        agora = cls._agora()

        payload = {
            "codigo_pedido": cls.gerar_codigo_pedido(),

            "origem": cls.ORIGEM_BALCAO,
            "tipo": cls.ORIGEM_BALCAO,
            "canal": cls.ORIGEM_BALCAO,

            "status": cls.STATUS_CRIADO,
            "situacao_pagamento": cls.PAGAMENTO_PENDENTE,

            "pagamento_status": "AGUARDANDO_PAGAMENTO",
            "pagamento_status_descricao": "Aguardando pagamento",

            "unidade_id": unidade["id"],
            "unidade_nome": unidade.get("nome", ""),

            "cliente_id": cliente["id"],
            "cliente_nome": cliente.get("nome", ""),
            "cliente_email": cliente.get("email", ""),
            "cliente_telefone": cliente.get("telefone", ""),

            "itens": itens_processados,

            "quantidade_itens": len(itens_processados),
            "quantidade_total_itens": totais["quantidade_total"],

            "subtotal": totais["subtotal"],
            "total": totais["total"],

            "valor_produtos": totais["subtotal"],
            "valor_desconto": 0.0,
            "valor_entrega": 0.0,
            "valor_total": totais["total"],
            "valor_total_formatado": cls._formatar_moeda(totais["total"]),

            "forma_pagamento": forma_pagamento,
            "pagamento_metodo": forma_pagamento,
            "pagamento_metodo_descricao": forma_pagamento,
            "pagamento_valor": totais["total"],
            "pagamento_valor_formatado": cls._formatar_moeda(totais["total"]),
            "pagamento_transacao_id": "",
            "pago_em": "",

            "observacao": observacao.strip(),

            "usuario_id": usuario_id,
            "usuario_nome": usuario_nome,

            "criado_em": agora.isoformat(),
            "criado_em_texto": cls._agora_texto(),
            "criado_em_ord": agora.strftime("%Y-%m-%d %H:%M:%S"),

            "atualizado_em": agora.isoformat(),
            "atualizado_em_texto": cls._agora_texto(),
        }

        doc_ref = FirebaseService.get_collection(cls.COLECAO_PEDIDOS).document()
        doc_ref.set(payload)
        return doc_ref.id

    @classmethod
    def buscar_pedido_por_id(cls, pedido_id: str) -> Optional[Dict[str, Any]]:
        if not pedido_id:
            return None

        doc = FirebaseService.get_collection(cls.COLECAO_PEDIDOS).document(pedido_id).get()
        if not doc.exists:
            return None

        data = doc.to_dict() or {}
        data["id"] = doc.id
        return data

    @classmethod
    def pedido_permite_edicao(cls, pedido: Dict[str, Any] | None) -> bool:
        if not pedido:
            return False

        return (pedido.get("status") or "").upper() in cls.STATUS_PERMITEM_EDICAO

    @classmethod
    def atualizar_pedido_balcao(
        cls,
        pedido_id: str,
        cliente_id: str,
        itens: List[Dict[str, Any]],
        forma_pagamento: str,
        observacao: str = "",
        usuario_nome: str = "",
        usuario_id: str = ""
    ) -> None:
        pedido = cls.buscar_pedido_por_id(pedido_id)
        if not pedido:
            raise ValueError("Pedido não encontrado.")

        if not cls.pedido_permite_edicao(pedido):
            raise ValueError("Este pedido não pode mais ser editado.")

        if not cliente_id:
            raise ValueError("Selecione o cliente.")

        if not itens:
            raise ValueError("Adicione ao menos um item ao pedido.")

        if not forma_pagamento:
            raise ValueError("Selecione a forma de pagamento.")

        cliente = cls.buscar_cliente_por_id(cliente_id)
        if not cliente:
            raise ValueError("Cliente não encontrado.")

        itens_processados = cls._processar_itens(itens)
        totais = cls.calcular_totais(itens_processados)
        agora = cls._agora()

        payload = {
            "origem": cls.ORIGEM_BALCAO,
            "tipo": cls.ORIGEM_BALCAO,
            "canal": cls.ORIGEM_BALCAO,

            "cliente_id": cliente["id"],
            "cliente_nome": cliente.get("nome", ""),
            "cliente_email": cliente.get("email", ""),
            "cliente_telefone": cliente.get("telefone", ""),

            "itens": itens_processados,

            "quantidade_itens": len(itens_processados),
            "quantidade_total_itens": totais["quantidade_total"],

            "subtotal": totais["subtotal"],
            "total": totais["total"],

            "valor_produtos": totais["subtotal"],
            "valor_desconto": 0.0,
            "valor_entrega": 0.0,
            "valor_total": totais["total"],
            "valor_total_formatado": cls._formatar_moeda(totais["total"]),

            "forma_pagamento": forma_pagamento,
            "pagamento_metodo": forma_pagamento,
            "pagamento_metodo_descricao": forma_pagamento,
            "pagamento_valor": totais["total"],
            "pagamento_valor_formatado": cls._formatar_moeda(totais["total"]),

            "observacao": observacao.strip(),

            "atualizado_em": agora.isoformat(),
            "atualizado_em_texto": cls._agora_texto(),
            "editado_por_id": usuario_id,
            "editado_por_nome": usuario_nome,
        }

        FirebaseService.get_collection(cls.COLECAO_PEDIDOS).document(pedido_id).update(payload)

    @classmethod
    def atualizar_status(
        cls,
        pedido_id: str,
        novo_status: str,
        usuario_nome: str = "",
        usuario_id: str = "",
    ) -> None:
        pedido = cls.buscar_pedido_por_id(pedido_id)
        if not pedido:
            raise ValueError("Pedido não encontrado.")

        novo_status = (novo_status or "").strip().upper()
        if novo_status not in cls.STATUS_VALIDOS:
            raise ValueError("Status inválido.")

        agora = cls._agora()

        payload = {
            "status": novo_status,
            "atualizado_em": agora.isoformat(),
            "atualizado_em_texto": cls._agora_texto(),
            "status_atualizado_por_id": usuario_id,
            "status_atualizado_por_nome": usuario_nome,
        }

        FirebaseService.get_collection(cls.COLECAO_PEDIDOS).document(pedido_id).update(payload)

    @classmethod
    def confirmar_pagamento(
        cls,
        pedido_id: str,
        usuario_nome: str = "",
        usuario_id: str = "",
    ) -> None:
        pedido = cls.buscar_pedido_por_id(pedido_id)
        if not pedido:
            raise ValueError("Pedido não encontrado.")

        if (pedido.get("status") or "").upper() == cls.STATUS_CANCELADO:
            raise ValueError("Não é possível confirmar pagamento de pedido cancelado.")

        agora = cls._agora()

        payload = {
            "situacao_pagamento": cls.PAGAMENTO_PAGO,
            "pagamento_status": "PAGO",
            "pagamento_status_descricao": "Pago",
            "pago_em": agora.isoformat(),
            "pago_em_texto": cls._agora_texto(),
            "pagamento_confirmado_por_id": usuario_id,
            "pagamento_confirmado_por_nome": usuario_nome,
            "atualizado_em": agora.isoformat(),
            "atualizado_em_texto": cls._agora_texto(),
        }

        FirebaseService.get_collection(cls.COLECAO_PEDIDOS).document(pedido_id).update(payload)

    @classmethod
    def cancelar_pedido(
        cls,
        pedido_id: str,
        usuario_nome: str = "",
        usuario_id: str = "",
    ) -> None:
        cls.atualizar_status(
            pedido_id=pedido_id,
            novo_status=cls.STATUS_CANCELADO,
            usuario_nome=usuario_nome,
            usuario_id=usuario_id,
        )