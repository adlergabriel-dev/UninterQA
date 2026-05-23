from datetime import datetime, date, time
from typing import Optional, Dict, Any, List

from services.firebase_service import FirebaseService


class RelatorioProdutosVendidosService:
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
    def _pedido_cancelado(cls, pedido: Dict[str, Any]):
        status = cls._normalizar_upper(
            pedido.get("status")
            or pedido.get("status_pedido")
        )

        situacao_pagamento = cls._normalizar_upper(
            pedido.get("situacao_pagamento")
            or pedido.get("pagamento_status")
            or pedido.get("status_pagamento")
            or pedido.get("statusPagamento")
        )

        if status in ["CANCELADO", "CANCELADA"]:
            return True

        if situacao_pagamento in ["CANCELADO", "ESTORNADO"]:
            return True

        return False

    @classmethod
    def _obter_nome_produto(cls, item: Dict[str, Any]):
        return (
            item.get("produto_nome")
            or item.get("nome_produto")
            or item.get("nome")
            or item.get("descricao")
            or item.get("produto")
            or "Produto não informado"
        )

    @classmethod
    def _obter_produto_id(cls, item: Dict[str, Any]):
        return (
            item.get("produto_id")
            or item.get("id_produto")
            or item.get("id")
            or ""
        )

    @classmethod
    def _obter_quantidade(cls, item: Dict[str, Any]):
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
    def _obter_valor_unitario(cls, item: Dict[str, Any]):
        valor = (
            item.get("valor_unitario")
            or item.get("preco_unitario")
            or item.get("preco")
            or item.get("valor")
            or 0
        )

        return cls._to_float(valor)

    @classmethod
    def _obter_valor_total_item(cls, item: Dict[str, Any], quantidade: int, valor_unitario: float):
        valor = (
            item.get("valor_total")
            or item.get("total")
            or item.get("subtotal")
            or item.get("valor_subtotal")
        )

        valor_total = cls._to_float(valor)

        if valor_total <= 0:
            valor_total = quantidade * valor_unitario

        return valor_total

    @classmethod
    def gerar_relatorio(
        cls,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        unidade_id: Optional[str] = None,
        produto: Optional[str] = None,
        origem: Optional[str] = None,
        ignorar_cancelados: bool = True,
    ):
        dt_inicio = cls._converter_data_filtro(data_inicio)
        dt_fim = cls._converter_data_filtro(data_fim, fim_dia=True)

        unidade_id = cls._normalizar_texto(unidade_id)
        produto = cls._normalizar_texto(produto).lower()
        origem = cls._normalizar_upper(origem)

        docs = FirebaseService.get_collection(cls.COLECAO_PEDIDOS).stream()

        linhas_detalhe = []
        agrupado = {}

        for doc in docs:
            pedido = doc.to_dict() or {}

            if not cls._origem_permitida(pedido, origem):
                continue

            if ignorar_cancelados and cls._pedido_cancelado(pedido):
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

            itens = pedido.get("itens") or []

            if not isinstance(itens, list):
                continue

            origem_pedido = cls._obter_origem(pedido)
            origem_formatada = cls._formatar_origem(origem_pedido)

            unidade_nome = pedido.get("unidade_nome") or pedido.get("filial_nome") or "-"
            codigo_pedido = pedido.get("codigo_pedido") or pedido.get("codigo") or doc.id
            cliente_nome = pedido.get("cliente_nome") or pedido.get("nome_cliente") or "-"

            for item in itens:
                if not isinstance(item, dict):
                    continue

                produto_id = cls._obter_produto_id(item)
                produto_nome = cls._normalizar_texto(cls._obter_nome_produto(item))

                if produto and produto not in produto_nome.lower():
                    continue

                quantidade = cls._obter_quantidade(item)
                valor_unitario = cls._obter_valor_unitario(item)
                valor_total = cls._obter_valor_total_item(item, quantidade, valor_unitario)

                chave = f"{pedido_unidade_id}|{origem_pedido}|{produto_id}|{produto_nome.lower()}"

                if chave not in agrupado:
                    agrupado[chave] = {
                        "produto_id": produto_id,
                        "produto_nome": produto_nome,
                        "unidade_id": pedido_unidade_id,
                        "unidade_nome": unidade_nome,
                        "origem": origem_pedido,
                        "origem_formatada": origem_formatada,
                        "quantidade": 0,
                        "valor_total": 0.0,
                        "valor_unitario_medio": 0.0,
                        "pedidos": 0,
                    }

                agrupado[chave]["quantidade"] += quantidade
                agrupado[chave]["valor_total"] += valor_total
                agrupado[chave]["pedidos"] += 1

                linhas_detalhe.append({
                    "codigo_pedido": codigo_pedido,
                    "data_obj": data_pedido,
                    "data_formatada": cls._formatar_data(data_pedido),
                    "cliente_nome": cliente_nome,
                    "unidade_id": pedido_unidade_id,
                    "unidade_nome": unidade_nome,
                    "origem": origem_pedido,
                    "origem_formatada": origem_formatada,
                    "produto_id": produto_id,
                    "produto_nome": produto_nome,
                    "quantidade": quantidade,
                    "valor_unitario": valor_unitario,
                    "valor_total": valor_total,
                })

        linhas = list(agrupado.values())

        for linha in linhas:
            quantidade = linha.get("quantidade", 0)
            valor_total = linha.get("valor_total", 0)

            if quantidade > 0:
                linha["valor_unitario_medio"] = valor_total / quantidade
            else:
                linha["valor_unitario_medio"] = 0.0

        linhas.sort(
            key=lambda x: (x.get("quantidade", 0), x.get("valor_total", 0)),
            reverse=True
        )

        linhas_detalhe.sort(
            key=lambda x: x.get("data_obj") or datetime.min,
            reverse=True
        )

        totais = cls._calcular_totais(linhas, linhas_detalhe)

        return {
            "linhas": linhas,
            "linhas_detalhe": linhas_detalhe,
            "totais": totais,
        }

    @classmethod
    def _calcular_totais(cls, linhas: List[Dict[str, Any]], linhas_detalhe: List[Dict[str, Any]]):
        total_produtos_diferentes = len(linhas)
        total_quantidade = sum(x.get("quantidade", 0) for x in linhas)
        total_vendido = sum(x.get("valor_total", 0) for x in linhas)
        total_lancamentos = len(linhas_detalhe)

        ticket_medio_produto = 0.0

        if total_quantidade > 0:
            ticket_medio_produto = total_vendido / total_quantidade

        resumo_por_filial = {}
        resumo_por_origem = {}

        for linha in linhas:
            filial = linha.get("unidade_nome") or "-"
            origem = linha.get("origem_formatada") or "-"

            resumo_por_filial.setdefault(filial, {
                "produtos_diferentes": 0,
                "quantidade": 0,
                "valor_total": 0.0,
            })

            resumo_por_origem.setdefault(origem, {
                "produtos_diferentes": 0,
                "quantidade": 0,
                "valor_total": 0.0,
            })

            resumo_por_filial[filial]["produtos_diferentes"] += 1
            resumo_por_filial[filial]["quantidade"] += linha.get("quantidade", 0)
            resumo_por_filial[filial]["valor_total"] += linha.get("valor_total", 0)

            resumo_por_origem[origem]["produtos_diferentes"] += 1
            resumo_por_origem[origem]["quantidade"] += linha.get("quantidade", 0)
            resumo_por_origem[origem]["valor_total"] += linha.get("valor_total", 0)

        return {
            "total_produtos_diferentes": total_produtos_diferentes,
            "total_quantidade": total_quantidade,
            "total_vendido": total_vendido,
            "total_lancamentos": total_lancamentos,
            "ticket_medio_produto": ticket_medio_produto,
            "resumo_por_filial": resumo_por_filial,
            "resumo_por_origem": resumo_por_origem,
        }