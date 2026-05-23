from datetime import datetime, date, time
from typing import Optional, Dict, Any, List

from services.firebase_service import FirebaseService


class RelatorioClientesCompraramService:
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
        cliente: Optional[str] = None,
        origem: Optional[str] = None,
        ignorar_cancelados: bool = True,
    ):
        dt_inicio = cls._converter_data_filtro(data_inicio)
        dt_fim = cls._converter_data_filtro(data_fim, fim_dia=True)

        unidade_id = cls._normalizar_texto(unidade_id)
        cliente = cls._normalizar_texto(cliente).lower()
        origem = cls._normalizar_upper(origem)

        docs = FirebaseService.get_collection(cls.COLECAO_PEDIDOS).stream()

        clientes = {}
        linhas_detalhe = []

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

            cliente_id = pedido.get("cliente_id") or pedido.get("id_cliente") or ""
            cliente_nome = pedido.get("cliente_nome") or pedido.get("nome_cliente") or "Cliente não informado"
            cliente_telefone = pedido.get("cliente_telefone") or pedido.get("telefone_cliente") or "-"

            if cliente and cliente not in cliente_nome.lower() and cliente not in cliente_telefone.lower():
                continue

            origem_pedido = cls._obter_origem(pedido)
            origem_formatada = cls._formatar_origem(origem_pedido)

            unidade_nome = pedido.get("unidade_nome") or pedido.get("filial_nome") or "-"
            codigo_pedido = pedido.get("codigo_pedido") or pedido.get("codigo") or doc.id
            status = cls._obter_status(pedido)
            situacao_pagamento = cls._obter_situacao_pagamento(pedido)

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

            chave = f"{origem_pedido}|{cliente_id or cliente_telefone or cliente_nome.lower()}"

            if chave not in clientes:
                clientes[chave] = {
                    "cliente_id": cliente_id,
                    "cliente_nome": cliente_nome,
                    "cliente_telefone": cliente_telefone,
                    "unidade_id": pedido_unidade_id,
                    "unidade_nome": unidade_nome,
                    "origem": origem_pedido,
                    "origem_formatada": origem_formatada,
                    "quantidade_pedidos": 0,
                    "quantidade_itens": 0,
                    "valor_total": 0.0,
                    "valor_pago": 0.0,
                    "valor_pendente": 0.0,
                    "valor_cancelado": 0.0,
                    "ticket_medio": 0.0,
                    "ultimo_pedido": None,
                    "ultimo_pedido_formatado": "-",
                }

            clientes[chave]["quantidade_pedidos"] += 1
            clientes[chave]["quantidade_itens"] += qtd_itens
            clientes[chave]["valor_total"] += valor_total

            if situacao_pagamento in ["PAGO", "APROVADO", "CONFIRMADO"]:
                clientes[chave]["valor_pago"] += valor_total

            elif situacao_pagamento in ["PENDENTE", "AGUARDANDO", "EM_ABERTO", "EM ABERTO"]:
                clientes[chave]["valor_pendente"] += valor_total

            elif situacao_pagamento in ["CANCELADO", "ESTORNADO"] or status in ["CANCELADO", "CANCELADA"]:
                clientes[chave]["valor_cancelado"] += valor_total

            ultimo_atual = clientes[chave].get("ultimo_pedido")

            if data_pedido and (not ultimo_atual or data_pedido > ultimo_atual):
                clientes[chave]["ultimo_pedido"] = data_pedido
                clientes[chave]["ultimo_pedido_formatado"] = cls._formatar_data(data_pedido)

            linhas_detalhe.append({
                "codigo_pedido": codigo_pedido,
                "data_obj": data_pedido,
                "data_formatada": cls._formatar_data(data_pedido),
                "cliente_nome": cliente_nome,
                "cliente_telefone": cliente_telefone,
                "unidade_nome": unidade_nome,
                "origem": origem_pedido,
                "origem_formatada": origem_formatada,
                "status": status,
                "situacao_pagamento": situacao_pagamento,
                "qtd_itens": qtd_itens,
                "valor_total": valor_total,
            })

        linhas = list(clientes.values())

        for linha in linhas:
            qtd_pedidos = linha.get("quantidade_pedidos", 0)
            valor_total = linha.get("valor_total", 0)

            if qtd_pedidos > 0:
                linha["ticket_medio"] = valor_total / qtd_pedidos
            else:
                linha["ticket_medio"] = 0.0

        linhas.sort(
            key=lambda x: (x.get("valor_total", 0), x.get("quantidade_pedidos", 0)),
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
        total_clientes = len(linhas)
        total_pedidos = sum(x.get("quantidade_pedidos", 0) for x in linhas)
        total_itens = sum(x.get("quantidade_itens", 0) for x in linhas)
        total_comprado = sum(x.get("valor_total", 0) for x in linhas)
        total_pago = sum(x.get("valor_pago", 0) for x in linhas)
        total_pendente = sum(x.get("valor_pendente", 0) for x in linhas)
        total_cancelado = sum(x.get("valor_cancelado", 0) for x in linhas)

        ticket_medio_geral = 0.0

        if total_pedidos > 0:
            ticket_medio_geral = total_comprado / total_pedidos

        resumo_por_filial = {}
        resumo_por_origem = {}

        for detalhe in linhas_detalhe:
            filial = detalhe.get("unidade_nome") or "-"
            origem = detalhe.get("origem_formatada") or "-"
            nome_cliente = detalhe.get("cliente_nome") or "-"

            resumo_por_filial.setdefault(filial, {
                "clientes": set(),
                "pedidos": 0,
                "valor_total": 0.0,
            })

            resumo_por_origem.setdefault(origem, {
                "clientes": set(),
                "pedidos": 0,
                "valor_total": 0.0,
            })

            resumo_por_filial[filial]["clientes"].add(nome_cliente)
            resumo_por_filial[filial]["pedidos"] += 1
            resumo_por_filial[filial]["valor_total"] += detalhe.get("valor_total", 0)

            resumo_por_origem[origem]["clientes"].add(nome_cliente)
            resumo_por_origem[origem]["pedidos"] += 1
            resumo_por_origem[origem]["valor_total"] += detalhe.get("valor_total", 0)

        for filial, item in resumo_por_filial.items():
            item["clientes"] = len(item["clientes"])

        for origem, item in resumo_por_origem.items():
            item["clientes"] = len(item["clientes"])

        return {
            "total_clientes": total_clientes,
            "total_pedidos": total_pedidos,
            "total_itens": total_itens,
            "total_comprado": total_comprado,
            "total_pago": total_pago,
            "total_pendente": total_pendente,
            "total_cancelado": total_cancelado,
            "ticket_medio_geral": ticket_medio_geral,
            "resumo_por_filial": resumo_por_filial,
            "resumo_por_origem": resumo_por_origem,
        }