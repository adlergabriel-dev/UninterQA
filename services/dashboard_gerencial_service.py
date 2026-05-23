from datetime import datetime, date, time
from typing import Optional, Dict, Any, List

from services.firebase_service import FirebaseService


class DashboardGerencialService:
    COLECAO_PEDIDOS = "pedidos"
    COLECAO_UNIDADES = "unidades"

    STATUS_ABERTO = "ABERTO"
    STATUS_CRIADO = "CRIADO"
    STATUS_EM_PREPARO = "EM_PREPARO"
    STATUS_PRONTO = "PRONTO"
    STATUS_ENVIADO = "ENVIADO"
    STATUS_ENTREGUE = "ENTREGUE"
    STATUS_FINALIZADO = "FINALIZADO"
    STATUS_CANCELADO = "CANCELADO"

    PAGAMENTO_AGUARDANDO = "AGUARDANDO_PAGAMENTO"
    PAGAMENTO_PENDENTE = "PENDENTE"
    PAGAMENTO_PAGO = "PAGO"
    PAGAMENTO_RECUSADO = "RECUSADO"

    ORIGENS_PERMITIDAS = [
        "BALCAO",
        "PEDIDO_BALCAO",
        "CLIENTE_WEB",
        "WEB",
    ]

    @classmethod
    def listar_unidades(cls) -> List[Dict[str, Any]]:
        docs = FirebaseService.get_collection(cls.COLECAO_UNIDADES).stream()

        unidades = []

        for doc in docs:
            item = doc.to_dict() or {}
            item["id"] = doc.id
            unidades.append(item)

        unidades.sort(key=lambda x: str(x.get("nome", "")).lower())
        return unidades

    @classmethod
    def _normalizar_texto(cls, valor):
        return str(valor or "").strip()

    @classmethod
    def _normalizar_upper(cls, valor):
        return str(valor or "").strip().upper()

    @classmethod
    def _to_float(cls, valor):
        if valor in [None, ""]:
            return 0.0

        try:
            if isinstance(valor, str):
                valor = (
                    valor.replace("R$", "")
                    .replace(".", "")
                    .replace(",", ".")
                    .strip()
                )

            return float(valor)
        except Exception:
            return 0.0

    @classmethod
    def _to_int(cls, valor):
        if valor in [None, ""]:
            return 0

        try:
            return int(float(str(valor).replace(",", ".").strip()))
        except Exception:
            return 0

    @classmethod
    def _converter_data_filtro(cls, valor: Optional[str], fim_dia: bool = False):
        if not valor:
            return None

        try:
            data = datetime.strptime(valor, "%Y-%m-%d").date()

            if fim_dia:
                return datetime.combine(data, time.max)

            return datetime.combine(data, time.min)
        except Exception:
            return None

    @classmethod
    def _converter_data_pedido(cls, pedido: Dict[str, Any]):
        campos_possiveis = [
            "criado_em_ord",
            "criado_em",
            "data_criacao",
            "data_pedido",
            "data_hora",
            "data",
            "criado_em_texto",
            "data_criacao_texto",
            "data_pedido_texto",
        ]

        for campo in campos_possiveis:
            valor = pedido.get(campo)

            if not valor:
                continue

            if isinstance(valor, datetime):
                return valor.replace(tzinfo=None)

            if isinstance(valor, date):
                return datetime.combine(valor, time.min)

            if hasattr(valor, "timestamp"):
                try:
                    return valor.replace(tzinfo=None)
                except Exception:
                    pass

            if isinstance(valor, str):
                valor_limpo = valor.strip()

                formatos = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%f",
                    "%d/%m/%Y %H:%M:%S",
                    "%d/%m/%Y %H:%M",
                    "%d/%m/%Y",
                    "%Y-%m-%d",
                ]

                for formato in formatos:
                    try:
                        return datetime.strptime(valor_limpo[:26], formato)
                    except Exception:
                        pass

        return None

    @classmethod
    def _formatar_data(cls, valor):
        if not valor:
            return "-"

        if isinstance(valor, datetime):
            return valor.strftime("%d/%m/%Y %H:%M")

        return str(valor)

    @classmethod
    def _obter_origem(cls, pedido: Dict[str, Any]):
        origem = cls._normalizar_upper(
            pedido.get("origem")
            or pedido.get("tipo")
            or pedido.get("canal")
            or ""
        )

        if origem == "PEDIDO_BALCAO":
            return "BALCAO"

        if origem == "WEB":
            return "CLIENTE_WEB"

        if not origem:
            return "NAO_INFORMADA"

        return origem

    @classmethod
    def _formatar_origem(cls, origem):
        origem = cls._normalizar_upper(origem)

        if origem in ["BALCAO", "PEDIDO_BALCAO"]:
            return "Balcão"

        if origem in ["CLIENTE_WEB", "WEB"]:
            return "Cliente Web"

        if origem == "NAO_INFORMADA":
            return "Não informada"

        return origem

    @classmethod
    def _origem_permitida(cls, pedido: Dict[str, Any], origem_filtro: Optional[str] = None):
        origem = cls._obter_origem(pedido)
        origem_filtro = cls._normalizar_upper(origem_filtro)

        if origem_filtro:
            if origem_filtro == "WEB":
                origem_filtro = "CLIENTE_WEB"

            if origem_filtro == "PEDIDO_BALCAO":
                origem_filtro = "BALCAO"

            return origem == origem_filtro

        if origem == "NAO_INFORMADA":
            return True

        return origem in ["BALCAO", "CLIENTE_WEB"]

    @classmethod
    def _obter_status(cls, pedido: Dict[str, Any]):
        status = cls._normalizar_upper(
            pedido.get("status")
            or pedido.get("status_pedido")
            or "ABERTO"
        )

        if status == cls.STATUS_CRIADO:
            return cls.STATUS_ABERTO

        if status == cls.STATUS_FINALIZADO:
            return cls.STATUS_ENTREGUE

        return status

    @classmethod
    def _obter_situacao_pagamento(cls, pedido: Dict[str, Any]):
        status = cls._normalizar_upper(
            pedido.get("pagamento_status")
            or pedido.get("situacao_pagamento")
            or pedido.get("status_pagamento")
            or pedido.get("statusPagamento")
            or "PENDENTE"
        )

        if status in ["AGUARDANDO", "AGUARDANDO PAGAMENTO", "AGUARDANDO_PGTO"]:
            return cls.PAGAMENTO_AGUARDANDO

        if status in ["EM_ABERTO", "EM ABERTO"]:
            return cls.PAGAMENTO_PENDENTE

        return status

    @classmethod
    def _pagamento_pago(cls, situacao_pagamento):
        return cls._normalizar_upper(situacao_pagamento) in [
            "PAGO",
            "APROVADO",
            "CONFIRMADO",
        ]

    @classmethod
    def _pagamento_pendente(cls, situacao_pagamento):
        return cls._normalizar_upper(situacao_pagamento) in [
            "PENDENTE",
            "AGUARDANDO",
            "AGUARDANDO_PAGAMENTO",
            "EM_ABERTO",
            "EM ABERTO",
        ]

    @classmethod
    def _pagamento_cancelado(cls, situacao_pagamento):
        return cls._normalizar_upper(situacao_pagamento) in [
            "CANCELADO",
            "ESTORNADO",
            "RECUSADO",
        ]

    @classmethod
    def _obter_forma_pagamento(cls, pedido: Dict[str, Any]):
        return cls._normalizar_texto(
            pedido.get("forma_pagamento")
            or pedido.get("pagamento_metodo")
            or pedido.get("pagamento_forma")
            or pedido.get("formaPagamento")
            or "-"
        )

    @classmethod
    def _calcular_total_itens(cls, pedido: Dict[str, Any]):
        quantidade_total_itens = cls._to_int(
            pedido.get("quantidade_total_itens")
            or pedido.get("qtd_total_itens")
        )

        if quantidade_total_itens > 0:
            return quantidade_total_itens

        itens = pedido.get("itens") or []
        total_qtd = 0

        if isinstance(itens, list):
            for item in itens:
                if not isinstance(item, dict):
                    continue

                quantidade = (
                    item.get("quantidade")
                    or item.get("qtd")
                    or item.get("qtde")
                    or 0
                )

                qtd = cls._to_int(quantidade)

                if qtd <= 0:
                    qtd = 1

                total_qtd += qtd

        return total_qtd

    @classmethod
    def _obter_valor_produtos(cls, pedido: Dict[str, Any]):
        valor = (
            pedido.get("valor_produtos")
            or pedido.get("subtotal")
            or pedido.get("valor_bruto")
            or pedido.get("total_produtos")
        )

        return cls._to_float(valor)

    @classmethod
    def _obter_valor_desconto(cls, pedido: Dict[str, Any]):
        valor = (
            pedido.get("valor_desconto")
            or pedido.get("desconto")
            or pedido.get("total_desconto")
        )

        return cls._to_float(valor)

    @classmethod
    def _obter_valor_entrega(cls, pedido: Dict[str, Any]):
        valor = (
            pedido.get("valor_entrega")
            or pedido.get("taxa_entrega")
            or pedido.get("entrega")
            or pedido.get("frete")
        )

        return cls._to_float(valor)

    @classmethod
    def _obter_valor_total(cls, pedido: Dict[str, Any], valor_produtos, valor_desconto, valor_entrega):
        valor = (
            pedido.get("valor_total")
            or pedido.get("total")
            or pedido.get("total_pedido")
            or pedido.get("valor_final")
            or pedido.get("pagamento_valor")
        )

        valor_total = cls._to_float(valor)

        if valor_total <= 0:
            valor_total = valor_produtos - valor_desconto + valor_entrega

        return valor_total

    @classmethod
    def _obter_nome_produto(cls, item: Dict[str, Any]):
        snapshot = item.get("snapshot_produto") or {}

        return cls._normalizar_texto(
            item.get("produto_nome")
            or item.get("nome_produto")
            or item.get("nome")
            or snapshot.get("produto_nome")
            or snapshot.get("nome")
            or item.get("descricao")
            or item.get("produto")
            or "Produto não informado"
        )

    @classmethod
    def _obter_quantidade_item(cls, item: Dict[str, Any]):
        quantidade = (
            item.get("quantidade")
            or item.get("qtd")
            or item.get("qtde")
            or 0
        )

        qtd = cls._to_int(quantidade)

        if qtd <= 0:
            qtd = 1

        return qtd

    @classmethod
    def _obter_valor_total_item(cls, item: Dict[str, Any], quantidade: int):
        snapshot = item.get("snapshot_produto") or {}

        valor_unitario = cls._to_float(
            item.get("valor_unitario")
            or item.get("preco_unitario")
            or item.get("preco")
            or item.get("valor")
            or snapshot.get("preco_unitario")
            or snapshot.get("preco")
            or 0
        )

        valor_total = cls._to_float(
            item.get("valor_total")
            or item.get("total")
            or item.get("subtotal")
            or item.get("valor_subtotal")
            or 0
        )

        if valor_total <= 0:
            valor_total = valor_unitario * quantidade

        return valor_total

    @classmethod
    def _classificar_operacional(cls, status, situacao_pagamento):
        status = cls._normalizar_upper(status)
        situacao_pagamento = cls._normalizar_upper(situacao_pagamento)

        if status in ["CANCELADO", "CANCELADA"] or cls._pagamento_cancelado(situacao_pagamento):
            return "cancelados"

        if cls._pagamento_pendente(situacao_pagamento):
            return "aguardando_pagamento"

        if cls._pagamento_pago(situacao_pagamento) and status == cls.STATUS_ABERTO:
            return "pagos_aguardando_cozinha"

        if cls._pagamento_pago(situacao_pagamento) and status == cls.STATUS_EM_PREPARO:
            return "em_preparo"

        if cls._pagamento_pago(situacao_pagamento) and status in [cls.STATUS_PRONTO, cls.STATUS_ENVIADO]:
            return "prontos_retirada"

        if cls._pagamento_pago(situacao_pagamento) and status in [cls.STATUS_ENTREGUE, cls.STATUS_FINALIZADO]:
            return "finalizados"

        return "outros"

    @classmethod
    def _novo_grupo_operacional(cls):
        return {
            "quantidade": 0,
            "valor_total": 0.0,
        }

    @classmethod
    def gerar_dashboard(
        cls,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        unidade_id: Optional[str] = None,
        origem: Optional[str] = None,
    ):
        dt_inicio = cls._converter_data_filtro(data_inicio)
        dt_fim = cls._converter_data_filtro(data_fim, fim_dia=True)

        unidade_id = cls._normalizar_texto(unidade_id)
        origem = cls._normalizar_upper(origem)

        docs = FirebaseService.get_collection(cls.COLECAO_PEDIDOS).stream()

        pedidos = []
        pedidos_operacionais = []

        resumo_por_filial = {}
        resumo_por_forma = {}
        resumo_por_status = {}
        resumo_por_pagamento = {}
        resumo_por_origem = {}
        produtos = {}

        operacional = {
            "aguardando_pagamento": cls._novo_grupo_operacional(),
            "pagos_aguardando_cozinha": cls._novo_grupo_operacional(),
            "em_preparo": cls._novo_grupo_operacional(),
            "prontos_retirada": cls._novo_grupo_operacional(),
            "finalizados": cls._novo_grupo_operacional(),
            "cancelados": cls._novo_grupo_operacional(),
            "outros": cls._novo_grupo_operacional(),
        }

        for doc in docs:
            pedido = doc.to_dict() or {}

            if not cls._origem_permitida(pedido, origem):
                continue

            data_pedido = cls._converter_data_pedido(pedido)

            if dt_inicio and not data_pedido:
                continue

            if dt_fim and not data_pedido:
                continue

            if dt_inicio and data_pedido and data_pedido < dt_inicio:
                continue

            if dt_fim and data_pedido and data_pedido > dt_fim:
                continue

            pedido_unidade_id = pedido.get("unidade_id") or pedido.get("filial_id") or ""

            if unidade_id and pedido_unidade_id != unidade_id:
                continue

            origem_pedido = cls._obter_origem(pedido)
            origem_formatada = cls._formatar_origem(origem_pedido)

            valor_produtos = cls._obter_valor_produtos(pedido)
            valor_desconto = cls._obter_valor_desconto(pedido)
            valor_entrega = cls._obter_valor_entrega(pedido)

            valor_total = cls._obter_valor_total(
                pedido,
                valor_produtos,
                valor_desconto,
                valor_entrega
            )

            status = cls._obter_status(pedido)
            situacao_pagamento = cls._obter_situacao_pagamento(pedido)
            forma_pagamento = cls._obter_forma_pagamento(pedido)
            qtd_itens = cls._calcular_total_itens(pedido)

            unidade_nome = pedido.get("unidade_nome") or pedido.get("filial_nome") or "-"
            cliente_nome = pedido.get("cliente_nome") or pedido.get("nome_cliente") or "-"

            grupo_operacional = cls._classificar_operacional(status, situacao_pagamento)

            linha = {
                "id": doc.id,
                "codigo_pedido": pedido.get("codigo_pedido") or pedido.get("codigo") or doc.id,
                "data_obj": data_pedido,
                "data_formatada": cls._formatar_data(data_pedido),
                "unidade_id": pedido_unidade_id,
                "unidade_nome": unidade_nome,
                "cliente_nome": cliente_nome,
                "status": status,
                "situacao_pagamento": situacao_pagamento,
                "forma_pagamento": forma_pagamento,
                "origem": origem_pedido,
                "origem_formatada": origem_formatada,
                "qtd_itens": qtd_itens,
                "valor_produtos": valor_produtos,
                "valor_desconto": valor_desconto,
                "valor_entrega": valor_entrega,
                "valor_total": valor_total,
                "grupo_operacional": grupo_operacional,
            }

            pedidos.append(linha)

            if grupo_operacional in operacional:
                operacional[grupo_operacional]["quantidade"] += 1
                operacional[grupo_operacional]["valor_total"] += valor_total

            if grupo_operacional not in ["finalizados", "cancelados"]:
                pedidos_operacionais.append(linha)

            resumo_por_filial.setdefault(unidade_nome, {
                "quantidade": 0,
                "valor_total": 0.0,
                "valor_pago": 0.0,
                "valor_pendente": 0.0,
                "valor_cancelado": 0.0,
            })

            resumo_por_forma.setdefault(forma_pagamento, {
                "quantidade": 0,
                "valor_total": 0.0,
            })

            resumo_por_status.setdefault(status, {
                "quantidade": 0,
                "valor_total": 0.0,
            })

            resumo_por_pagamento.setdefault(situacao_pagamento, {
                "quantidade": 0,
                "valor_total": 0.0,
            })

            resumo_por_origem.setdefault(origem_formatada, {
                "quantidade": 0,
                "valor_total": 0.0,
                "valor_pago": 0.0,
                "valor_pendente": 0.0,
                "valor_cancelado": 0.0,
            })

            resumo_por_filial[unidade_nome]["quantidade"] += 1
            resumo_por_filial[unidade_nome]["valor_total"] += valor_total

            resumo_por_forma[forma_pagamento]["quantidade"] += 1
            resumo_por_forma[forma_pagamento]["valor_total"] += valor_total

            resumo_por_status[status]["quantidade"] += 1
            resumo_por_status[status]["valor_total"] += valor_total

            resumo_por_pagamento[situacao_pagamento]["quantidade"] += 1
            resumo_por_pagamento[situacao_pagamento]["valor_total"] += valor_total

            resumo_por_origem[origem_formatada]["quantidade"] += 1
            resumo_por_origem[origem_formatada]["valor_total"] += valor_total

            if cls._pagamento_pago(situacao_pagamento):
                resumo_por_filial[unidade_nome]["valor_pago"] += valor_total
                resumo_por_origem[origem_formatada]["valor_pago"] += valor_total

            elif cls._pagamento_pendente(situacao_pagamento):
                resumo_por_filial[unidade_nome]["valor_pendente"] += valor_total
                resumo_por_origem[origem_formatada]["valor_pendente"] += valor_total

            elif cls._pagamento_cancelado(situacao_pagamento) or status in ["CANCELADO", "CANCELADA"]:
                resumo_por_filial[unidade_nome]["valor_cancelado"] += valor_total
                resumo_por_origem[origem_formatada]["valor_cancelado"] += valor_total

            itens = pedido.get("itens") or []

            if isinstance(itens, list):
                for item in itens:
                    if not isinstance(item, dict):
                        continue

                    produto_nome = cls._obter_nome_produto(item)
                    quantidade = cls._obter_quantidade_item(item)
                    valor_item = cls._obter_valor_total_item(item, quantidade)

                    produtos.setdefault(produto_nome, {
                        "produto_nome": produto_nome,
                        "quantidade": 0,
                        "valor_total": 0.0,
                        "pedidos": 0,
                    })

                    produtos[produto_nome]["quantidade"] += quantidade
                    produtos[produto_nome]["valor_total"] += valor_item
                    produtos[produto_nome]["pedidos"] += 1

        pedidos.sort(
            key=lambda x: x.get("data_obj") or datetime.min,
            reverse=True
        )

        pedidos_operacionais.sort(
            key=lambda x: x.get("data_obj") or datetime.min,
            reverse=True
        )

        produtos_lista = list(produtos.values())
        produtos_lista.sort(
            key=lambda x: (x.get("quantidade", 0), x.get("valor_total", 0)),
            reverse=True
        )

        ultimos_pedidos = pedidos[:10]
        produtos_mais_vendidos = produtos_lista[:10]

        total_pedidos = len(pedidos)
        total_itens = sum(x.get("qtd_itens", 0) for x in pedidos)
        total_produtos = sum(x.get("valor_produtos", 0) for x in pedidos)
        total_descontos = sum(x.get("valor_desconto", 0) for x in pedidos)
        total_entregas = sum(x.get("valor_entrega", 0) for x in pedidos)
        total_geral = sum(x.get("valor_total", 0) for x in pedidos)

        total_pago = sum(
            x.get("valor_total", 0)
            for x in pedidos
            if cls._pagamento_pago(x.get("situacao_pagamento"))
        )

        total_pendente = sum(
            x.get("valor_total", 0)
            for x in pedidos
            if cls._pagamento_pendente(x.get("situacao_pagamento"))
        )

        total_cancelado = sum(
            x.get("valor_total", 0)
            for x in pedidos
            if x.get("status") in ["CANCELADO", "CANCELADA"]
            or cls._pagamento_cancelado(x.get("situacao_pagamento"))
        )

        ticket_medio = 0.0

        if total_pedidos > 0:
            ticket_medio = total_geral / total_pedidos

        return {
            "totais": {
                "total_pedidos": total_pedidos,
                "total_itens": total_itens,
                "total_produtos": total_produtos,
                "total_descontos": total_descontos,
                "total_entregas": total_entregas,
                "total_geral": total_geral,
                "total_pago": total_pago,
                "total_pendente": total_pendente,
                "total_cancelado": total_cancelado,
                "ticket_medio": ticket_medio,
            },
            "operacional": operacional,
            "pedidos_operacionais": pedidos_operacionais[:15],
            "resumo_por_filial": resumo_por_filial,
            "resumo_por_forma": resumo_por_forma,
            "resumo_por_status": resumo_por_status,
            "resumo_por_pagamento": resumo_por_pagamento,
            "resumo_por_origem": resumo_por_origem,
            "produtos_mais_vendidos": produtos_mais_vendidos,
            "ultimos_pedidos": ultimos_pedidos,
        }