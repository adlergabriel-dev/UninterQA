from datetime import datetime, date, time
from typing import Optional, Dict, Any, List

from services.firebase_service import FirebaseService


class RelatorioPedidoBalcaoService:
    COLECAO_PEDIDOS = "pedidos"
    COLECAO_UNIDADES = "unidades"

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
                    "%d/%m/%Y %H:%M:%S",
                    "%d/%m/%Y %H:%M",
                    "%d/%m/%Y",
                    "%Y-%m-%d",
                ]

                for formato in formatos:
                    try:
                        return datetime.strptime(valor_limpo[:19], formato)
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
    def _calcular_total_itens(cls, pedido: Dict[str, Any]):
        itens = pedido.get("itens") or []
        total_qtd = 0

        if isinstance(itens, list):
            for item in itens:
                try:
                    total_qtd += int(item.get("quantidade", 0) or 0)
                except Exception:
                    pass

        return total_qtd

    @classmethod
    def _eh_pedido_balcao(cls, pedido: Dict[str, Any]):
        origem = cls._normalizar_upper(pedido.get("origem"))
        tipo = cls._normalizar_upper(pedido.get("tipo"))

        if origem in ["BALCAO", "PEDIDO_BALCAO"]:
            return True

        if tipo in ["BALCAO", "PEDIDO_BALCAO"]:
            return True

        return False

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
        )

        valor_total = cls._to_float(valor)

        if valor_total <= 0:
            valor_total = valor_produtos - valor_desconto + valor_entrega

        return valor_total

    @classmethod
    def _montar_linha(cls, doc_id: str, pedido: Dict[str, Any]):
        data_obj = cls._converter_data_pedido(pedido)

        valor_produtos = cls._obter_valor_produtos(pedido)
        valor_desconto = cls._obter_valor_desconto(pedido)
        valor_entrega = cls._obter_valor_entrega(pedido)
        valor_total = cls._obter_valor_total(
            pedido,
            valor_produtos,
            valor_desconto,
            valor_entrega
        )

        situacao_pagamento = (
            pedido.get("situacao_pagamento")
            or pedido.get("pagamento_status")
            or pedido.get("status_pagamento")
            or pedido.get("statusPagamento")
            or "PENDENTE"
        )

        forma_pagamento = (
            pedido.get("forma_pagamento")
            or pedido.get("pagamento_forma")
            or pedido.get("formaPagamento")
            or "-"
        )

        status = (
            pedido.get("status")
            or pedido.get("status_pedido")
            or "ABERTO"
        )

        return {
            "id": doc_id,
            "codigo_pedido": pedido.get("codigo_pedido") or pedido.get("codigo") or doc_id,
            "data_obj": data_obj,
            "data_formatada": cls._formatar_data(data_obj),
            "cliente_nome": pedido.get("cliente_nome") or pedido.get("nome_cliente") or "-",
            "cliente_telefone": pedido.get("cliente_telefone") or pedido.get("telefone_cliente") or "-",
            "unidade_id": pedido.get("unidade_id") or pedido.get("filial_id") or "",
            "unidade_nome": pedido.get("unidade_nome") or pedido.get("filial_nome") or "-",
            "status": cls._normalizar_upper(status),
            "forma_pagamento": cls._normalizar_texto(forma_pagamento),
            "situacao_pagamento": cls._normalizar_upper(situacao_pagamento),
            "qtd_itens": cls._calcular_total_itens(pedido),
            "valor_produtos": valor_produtos,
            "valor_desconto": valor_desconto,
            "valor_entrega": valor_entrega,
            "valor_total": valor_total,
            "observacao": pedido.get("observacao") or "",
            "origem": pedido.get("origem") or "BALCAO",
        }

    @classmethod
    def gerar_relatorio(
        cls,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        unidade_id: Optional[str] = None,
        status: Optional[str] = None,
        forma_pagamento: Optional[str] = None,
        situacao_pagamento: Optional[str] = None,
    ):
        dt_inicio = cls._converter_data_filtro(data_inicio)
        dt_fim = cls._converter_data_filtro(data_fim, fim_dia=True)

        unidade_id = cls._normalizar_texto(unidade_id)
        status = cls._normalizar_upper(status)
        forma_pagamento = cls._normalizar_texto(forma_pagamento).lower()
        situacao_pagamento = cls._normalizar_upper(situacao_pagamento)

        docs = FirebaseService.get_collection(cls.COLECAO_PEDIDOS).stream()

        linhas = []

        for doc in docs:
            pedido = doc.to_dict() or {}

            if not cls._eh_pedido_balcao(pedido):
                continue

            linha = cls._montar_linha(doc.id, pedido)

            data_pedido = linha.get("data_obj")

            if dt_inicio and data_pedido and data_pedido < dt_inicio:
                continue

            if dt_fim and data_pedido and data_pedido > dt_fim:
                continue

            if dt_inicio and not data_pedido:
                continue

            if dt_fim and not data_pedido:
                continue

            if unidade_id and linha.get("unidade_id") != unidade_id:
                continue

            if status and linha.get("status") != status:
                continue

            if forma_pagamento and linha.get("forma_pagamento", "").lower() != forma_pagamento:
                continue

            if situacao_pagamento and linha.get("situacao_pagamento") != situacao_pagamento:
                continue

            linhas.append(linha)

        linhas.sort(
            key=lambda x: x.get("data_obj") or datetime.min,
            reverse=True
        )

        totais = cls._calcular_totais(linhas)

        return {
            "linhas": linhas,
            "totais": totais,
        }

    @classmethod
    def _calcular_totais(cls, linhas: List[Dict[str, Any]]):
        total_pedidos = len(linhas)
        total_itens = sum(x.get("qtd_itens", 0) for x in linhas)
        total_produtos = sum(x.get("valor_produtos", 0) for x in linhas)
        total_descontos = sum(x.get("valor_desconto", 0) for x in linhas)
        total_entregas = sum(x.get("valor_entrega", 0) for x in linhas)
        total_geral = sum(x.get("valor_total", 0) for x in linhas)

        total_pago = sum(
            x.get("valor_total", 0)
            for x in linhas
            if x.get("situacao_pagamento") in ["PAGO", "APROVADO", "CONFIRMADO"]
        )

        total_pendente = sum(
            x.get("valor_total", 0)
            for x in linhas
            if x.get("situacao_pagamento") in ["PENDENTE", "AGUARDANDO", "EM_ABERTO", "EM ABERTO"]
        )

        total_cancelado = sum(
            x.get("valor_total", 0)
            for x in linhas
            if x.get("status") in ["CANCELADO", "CANCELADA"]
        )

        resumo_por_status = {}
        resumo_por_pagamento = {}
        resumo_por_forma = {}

        for linha in linhas:
            st = linha.get("status") or "-"
            pg = linha.get("situacao_pagamento") or "-"
            fp = linha.get("forma_pagamento") or "-"

            resumo_por_status.setdefault(st, {"quantidade": 0, "valor": 0.0})
            resumo_por_status[st]["quantidade"] += 1
            resumo_por_status[st]["valor"] += linha.get("valor_total", 0)

            resumo_por_pagamento.setdefault(pg, {"quantidade": 0, "valor": 0.0})
            resumo_por_pagamento[pg]["quantidade"] += 1
            resumo_por_pagamento[pg]["valor"] += linha.get("valor_total", 0)

            resumo_por_forma.setdefault(fp, {"quantidade": 0, "valor": 0.0})
            resumo_por_forma[fp]["quantidade"] += 1
            resumo_por_forma[fp]["valor"] += linha.get("valor_total", 0)

        return {
            "total_pedidos": total_pedidos,
            "total_itens": total_itens,
            "total_produtos": total_produtos,
            "total_descontos": total_descontos,
            "total_entregas": total_entregas,
            "total_geral": total_geral,
            "total_pago": total_pago,
            "total_pendente": total_pendente,
            "total_cancelado": total_cancelado,
            "resumo_por_status": resumo_por_status,
            "resumo_por_pagamento": resumo_por_pagamento,
            "resumo_por_forma": resumo_por_forma,
        }