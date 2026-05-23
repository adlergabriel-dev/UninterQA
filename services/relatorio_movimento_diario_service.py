from datetime import datetime, date, time
from typing import Optional, Dict, Any, List

from services.firebase_service import FirebaseService


class RelatorioMovimentoDiarioService:
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
            return valor.strftime("%d/%m/%Y")

        return str(valor)

    @classmethod
    def _formatar_data_hora(cls, valor):
        if not valor:
            return "-"

        if isinstance(valor, datetime):
            return valor.strftime("%d/%m/%Y %H:%M")

        return str(valor)

    @classmethod
    def _chave_data(cls, valor):
        if not valor:
            return "SEM_DATA"

        if isinstance(valor, datetime):
            return valor.strftime("%Y-%m-%d")

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
        return cls._normalizar_upper(
            pedido.get("status")
            or pedido.get("status_pedido")
            or "ABERTO"
        )

    @classmethod
    def _obter_situacao_pagamento(cls, pedido: Dict[str, Any]):
        return cls._normalizar_upper(
            pedido.get("situacao_pagamento")
            or pedido.get("pagamento_status")
            or pedido.get("status_pagamento")
            or pedido.get("statusPagamento")
            or "PENDENTE"
        )

    @classmethod
    def _calcular_total_itens(cls, pedido: Dict[str, Any]):
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
        )

        valor_total = cls._to_float(valor)

        if valor_total <= 0:
            valor_total = valor_produtos - valor_desconto + valor_entrega

        return valor_total

    @classmethod
    def gerar_relatorio(
        cls,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        unidade_id: Optional[str] = None,
        situacao_pagamento: Optional[str] = None,
        origem: Optional[str] = None,
    ):
        dt_inicio = cls._converter_data_filtro(data_inicio)
        dt_fim = cls._converter_data_filtro(data_fim, fim_dia=True)

        unidade_id = cls._normalizar_texto(unidade_id)
        situacao_pagamento = cls._normalizar_upper(situacao_pagamento)
        origem = cls._normalizar_upper(origem)

        docs = FirebaseService.get_collection(cls.COLECAO_PEDIDOS).stream()

        agrupado = {}
        linhas_detalhe = []

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

            status = cls._obter_status(pedido)
            situacao = cls._obter_situacao_pagamento(pedido)

            if situacao_pagamento and situacao != situacao_pagamento:
                continue

            origem_pedido = cls._obter_origem(pedido)
            origem_formatada = cls._formatar_origem(origem_pedido)

            unidade_nome = pedido.get("unidade_nome") or pedido.get("filial_nome") or "-"
            cliente_nome = pedido.get("cliente_nome") or pedido.get("nome_cliente") or "-"
            codigo_pedido = pedido.get("codigo_pedido") or pedido.get("codigo") or doc.id

            valor_produtos = cls._obter_valor_produtos(pedido)
            valor_desconto = cls._obter_valor_desconto(pedido)
            valor_entrega = cls._obter_valor_entrega(pedido)
            valor_total = cls._obter_valor_total(
                pedido,
                valor_produtos,
                valor_desconto,
                valor_entrega
            )

            qtd_itens = cls._calcular_total_itens(pedido)

            data_chave = cls._chave_data(data_pedido)
            data_formatada = cls._formatar_data(data_pedido)

            chave = f"{data_chave}|{pedido_unidade_id}|{origem_pedido}"

            if chave not in agrupado:
                agrupado[chave] = {
                    "data_chave": data_chave,
                    "data_formatada": data_formatada,
                    "unidade_id": pedido_unidade_id,
                    "unidade_nome": unidade_nome,
                    "origem": origem_pedido,
                    "origem_formatada": origem_formatada,
                    "quantidade_pedidos": 0,
                    "quantidade_itens": 0,
                    "valor_produtos": 0.0,
                    "valor_descontos": 0.0,
                    "valor_entregas": 0.0,
                    "valor_total": 0.0,
                    "valor_pago": 0.0,
                    "valor_pendente": 0.0,
                    "valor_cancelado": 0.0,
                    "ticket_medio": 0.0,
                }

            agrupado[chave]["quantidade_pedidos"] += 1
            agrupado[chave]["quantidade_itens"] += qtd_itens
            agrupado[chave]["valor_produtos"] += valor_produtos
            agrupado[chave]["valor_descontos"] += valor_desconto
            agrupado[chave]["valor_entregas"] += valor_entrega
            agrupado[chave]["valor_total"] += valor_total

            if situacao in ["PAGO", "APROVADO", "CONFIRMADO"]:
                agrupado[chave]["valor_pago"] += valor_total

            elif situacao in ["PENDENTE", "AGUARDANDO", "EM_ABERTO", "EM ABERTO"]:
                agrupado[chave]["valor_pendente"] += valor_total

            elif situacao in ["CANCELADO", "ESTORNADO"] or status in ["CANCELADO", "CANCELADA"]:
                agrupado[chave]["valor_cancelado"] += valor_total

            linhas_detalhe.append({
                "codigo_pedido": codigo_pedido,
                "data_obj": data_pedido,
                "data_formatada": cls._formatar_data_hora(data_pedido),
                "origem": origem_pedido,
                "origem_formatada": origem_formatada,
                "unidade_nome": unidade_nome,
                "cliente_nome": cliente_nome,
                "status": status,
                "situacao_pagamento": situacao,
                "qtd_itens": qtd_itens,
                "valor_total": valor_total,
            })

        linhas = list(agrupado.values())

        for linha in linhas:
            qtd_pedidos = linha.get("quantidade_pedidos", 0)
            valor_total = linha.get("valor_total", 0)

            if qtd_pedidos > 0:
                linha["ticket_medio"] = valor_total / qtd_pedidos
            else:
                linha["ticket_medio"] = 0.0

        linhas.sort(
            key=lambda x: (x.get("data_chave", ""), x.get("unidade_nome", ""), x.get("origem_formatada", "")),
            reverse=True
        )

        linhas_detalhe.sort(
            key=lambda x: x.get("data_obj") or datetime.min,
            reverse=True
        )

        totais = cls._calcular_totais(linhas)

        return {
            "linhas": linhas,
            "linhas_detalhe": linhas_detalhe,
            "totais": totais,
        }

    @classmethod
    def _calcular_totais(cls, linhas: List[Dict[str, Any]]):
        total_dias = len(set(x.get("data_chave") for x in linhas if x.get("data_chave")))
        total_linhas = len(linhas)
        total_pedidos = sum(x.get("quantidade_pedidos", 0) for x in linhas)
        total_itens = sum(x.get("quantidade_itens", 0) for x in linhas)
        total_produtos = sum(x.get("valor_produtos", 0) for x in linhas)
        total_descontos = sum(x.get("valor_descontos", 0) for x in linhas)
        total_entregas = sum(x.get("valor_entregas", 0) for x in linhas)
        total_geral = sum(x.get("valor_total", 0) for x in linhas)
        total_pago = sum(x.get("valor_pago", 0) for x in linhas)
        total_pendente = sum(x.get("valor_pendente", 0) for x in linhas)
        total_cancelado = sum(x.get("valor_cancelado", 0) for x in linhas)

        ticket_medio = 0.0

        if total_pedidos > 0:
            ticket_medio = total_geral / total_pedidos

        resumo_por_filial = {}
        resumo_por_origem = {}

        for linha in linhas:
            filial = linha.get("unidade_nome") or "-"
            origem = linha.get("origem_formatada") or "-"

            resumo_por_filial.setdefault(filial, {
                "dias": set(),
                "pedidos": 0,
                "itens": 0,
                "valor_total": 0.0,
                "valor_pago": 0.0,
                "valor_pendente": 0.0,
            })

            resumo_por_origem.setdefault(origem, {
                "dias": set(),
                "pedidos": 0,
                "itens": 0,
                "valor_total": 0.0,
                "valor_pago": 0.0,
                "valor_pendente": 0.0,
            })

            resumo_por_filial[filial]["dias"].add(linha.get("data_chave"))
            resumo_por_filial[filial]["pedidos"] += linha.get("quantidade_pedidos", 0)
            resumo_por_filial[filial]["itens"] += linha.get("quantidade_itens", 0)
            resumo_por_filial[filial]["valor_total"] += linha.get("valor_total", 0)
            resumo_por_filial[filial]["valor_pago"] += linha.get("valor_pago", 0)
            resumo_por_filial[filial]["valor_pendente"] += linha.get("valor_pendente", 0)

            resumo_por_origem[origem]["dias"].add(linha.get("data_chave"))
            resumo_por_origem[origem]["pedidos"] += linha.get("quantidade_pedidos", 0)
            resumo_por_origem[origem]["itens"] += linha.get("quantidade_itens", 0)
            resumo_por_origem[origem]["valor_total"] += linha.get("valor_total", 0)
            resumo_por_origem[origem]["valor_pago"] += linha.get("valor_pago", 0)
            resumo_por_origem[origem]["valor_pendente"] += linha.get("valor_pendente", 0)

        for filial, item in resumo_por_filial.items():
            item["dias"] = len(item["dias"])

        for origem, item in resumo_por_origem.items():
            item["dias"] = len(item["dias"])

        return {
            "total_dias": total_dias,
            "total_linhas": total_linhas,
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
            "resumo_por_filial": resumo_por_filial,
            "resumo_por_origem": resumo_por_origem,
        }