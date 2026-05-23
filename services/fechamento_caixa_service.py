from datetime import datetime, date, time
from typing import Optional, Dict, Any, List

from services.firebase_service import FirebaseService
from services.auditoria_service import AuditoriaService


class FechamentoCaixaService:
    COLECAO_PEDIDOS = "pedidos"
    COLECAO_UNIDADES = "unidades"
    COLECAO_FECHAMENTOS = "fechamentos_caixa"

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
    def _agora_iso(cls):
        return datetime.utcnow().isoformat()

    @classmethod
    def _agora_ord(cls):
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def _agora_texto(cls):
        return datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")

    @classmethod
    def _formatar_moeda(cls, valor):
        return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

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

        forma_pagamento = (
            pedido.get("forma_pagamento")
            or pedido.get("pagamento_forma")
            or pedido.get("pagamento_metodo")
            or pedido.get("formaPagamento")
            or "-"
        )

        situacao_pagamento = (
            pedido.get("situacao_pagamento")
            or pedido.get("pagamento_status")
            or pedido.get("status_pagamento")
            or pedido.get("statusPagamento")
            or "PENDENTE"
        )

        status = (
            pedido.get("status")
            or pedido.get("status_pedido")
            or "ABERTO"
        )

        origem = cls._obter_origem(pedido)

        return {
            "id": doc_id,
            "codigo_pedido": pedido.get("codigo_pedido") or pedido.get("codigo") or doc_id,
            "data_obj": data_obj,
            "data_formatada": cls._formatar_data(data_obj),
            "unidade_id": pedido.get("unidade_id") or pedido.get("filial_id") or "",
            "unidade_nome": pedido.get("unidade_nome") or pedido.get("filial_nome") or "-",
            "cliente_nome": pedido.get("cliente_nome") or pedido.get("nome_cliente") or "-",
            "status": cls._normalizar_upper(status),
            "origem": origem,
            "origem_formatada": cls._formatar_origem(origem),
            "forma_pagamento": cls._normalizar_texto(forma_pagamento),
            "situacao_pagamento": cls._normalizar_upper(situacao_pagamento),
            "qtd_itens": cls._calcular_total_itens(pedido),
            "valor_produtos": valor_produtos,
            "valor_desconto": valor_desconto,
            "valor_entrega": valor_entrega,
            "valor_total": valor_total,
        }

    @classmethod
    def gerar_fechamento(
        cls,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        unidade_id: Optional[str] = None,
        forma_pagamento: Optional[str] = None,
        situacao_pagamento: Optional[str] = None,
        origem: Optional[str] = None,
    ):
        dt_inicio = cls._converter_data_filtro(data_inicio)
        dt_fim = cls._converter_data_filtro(data_fim, fim_dia=True)

        unidade_id = cls._normalizar_texto(unidade_id)
        forma_pagamento = cls._normalizar_texto(forma_pagamento).lower()
        situacao_pagamento = cls._normalizar_upper(situacao_pagamento)
        origem = cls._normalizar_upper(origem)

        docs = FirebaseService.get_collection(cls.COLECAO_PEDIDOS).stream()

        linhas = []

        for doc in docs:
            pedido = doc.to_dict() or {}

            if not cls._origem_permitida(pedido, origem):
                continue

            linha = cls._montar_linha(doc.id, pedido)

            data_pedido = linha.get("data_obj")

            if dt_inicio and not data_pedido:
                continue

            if dt_fim and not data_pedido:
                continue

            if dt_inicio and data_pedido and data_pedido < dt_inicio:
                continue

            if dt_fim and data_pedido and data_pedido > dt_fim:
                continue

            if unidade_id and linha.get("unidade_id") != unidade_id:
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
            if x.get("situacao_pagamento") in [
                "PENDENTE",
                "AGUARDANDO",
                "AGUARDANDO_PAGAMENTO",
                "EM_ABERTO",
                "EM ABERTO",
            ]
        )

        total_cancelado = sum(
            x.get("valor_total", 0)
            for x in linhas
            if x.get("status") in ["CANCELADO", "CANCELADA"]
            or x.get("situacao_pagamento") in ["CANCELADO", "ESTORNADO", "RECUSADO"]
        )

        resumo_por_forma = {}
        resumo_por_pagamento = {}
        resumo_por_filial = {}
        resumo_por_origem = {}

        for linha in linhas:
            forma = linha.get("forma_pagamento") or "-"
            pagamento = linha.get("situacao_pagamento") or "-"
            filial = linha.get("unidade_nome") or "-"
            origem = linha.get("origem_formatada") or "-"

            resumo_por_forma.setdefault(forma, {
                "quantidade": 0,
                "valor_total": 0.0,
                "valor_pago": 0.0,
                "valor_pendente": 0.0,
                "valor_cancelado": 0.0,
            })

            resumo_por_pagamento.setdefault(pagamento, {
                "quantidade": 0,
                "valor_total": 0.0,
            })

            resumo_por_filial.setdefault(filial, {
                "quantidade": 0,
                "valor_total": 0.0,
                "valor_pago": 0.0,
                "valor_pendente": 0.0,
                "valor_cancelado": 0.0,
            })

            resumo_por_origem.setdefault(origem, {
                "quantidade": 0,
                "valor_total": 0.0,
                "valor_pago": 0.0,
                "valor_pendente": 0.0,
                "valor_cancelado": 0.0,
            })

            valor = linha.get("valor_total", 0)
            situacao = linha.get("situacao_pagamento")
            status = linha.get("status")

            resumo_por_forma[forma]["quantidade"] += 1
            resumo_por_forma[forma]["valor_total"] += valor

            resumo_por_pagamento[pagamento]["quantidade"] += 1
            resumo_por_pagamento[pagamento]["valor_total"] += valor

            resumo_por_filial[filial]["quantidade"] += 1
            resumo_por_filial[filial]["valor_total"] += valor

            resumo_por_origem[origem]["quantidade"] += 1
            resumo_por_origem[origem]["valor_total"] += valor

            if situacao in ["PAGO", "APROVADO", "CONFIRMADO"]:
                resumo_por_forma[forma]["valor_pago"] += valor
                resumo_por_filial[filial]["valor_pago"] += valor
                resumo_por_origem[origem]["valor_pago"] += valor

            elif situacao in ["PENDENTE", "AGUARDANDO", "AGUARDANDO_PAGAMENTO", "EM_ABERTO", "EM ABERTO"]:
                resumo_por_forma[forma]["valor_pendente"] += valor
                resumo_por_filial[filial]["valor_pendente"] += valor
                resumo_por_origem[origem]["valor_pendente"] += valor

            elif situacao in ["CANCELADO", "ESTORNADO", "RECUSADO"] or status in ["CANCELADO", "CANCELADA"]:
                resumo_por_forma[forma]["valor_cancelado"] += valor
                resumo_por_filial[filial]["valor_cancelado"] += valor
                resumo_por_origem[origem]["valor_cancelado"] += valor

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
            "resumo_por_forma": resumo_por_forma,
            "resumo_por_pagamento": resumo_por_pagamento,
            "resumo_por_filial": resumo_por_filial,
            "resumo_por_origem": resumo_por_origem,
        }

    @classmethod
    def buscar_unidade_por_id(cls, unidade_id: str):
        unidade_id = cls._normalizar_texto(unidade_id)

        if not unidade_id:
            return None

        doc = FirebaseService.get_collection(cls.COLECAO_UNIDADES).document(unidade_id).get()

        if not doc.exists:
            return None

        data = doc.to_dict() or {}
        data["id"] = doc.id
        return data

    @classmethod
    def listar_fechamentos(cls, limite: int = 100):
        docs = FirebaseService.get_collection(cls.COLECAO_FECHAMENTOS).stream()

        fechamentos = []

        for doc in docs:
            item = doc.to_dict() or {}
            item["id"] = doc.id
            fechamentos.append(item)

        fechamentos.sort(
            key=lambda x: x.get("criado_em_ord") or x.get("criado_em") or "",
            reverse=True
        )

        if limite and limite > 0:
            return fechamentos[:limite]

        return fechamentos

    @classmethod
    def fechamento_ja_existe(cls, data_inicio: str, data_fim: str, unidade_id: str):
        data_inicio = cls._normalizar_texto(data_inicio)
        data_fim = cls._normalizar_texto(data_fim)
        unidade_id = cls._normalizar_texto(unidade_id)

        docs = FirebaseService.get_collection(cls.COLECAO_FECHAMENTOS).stream()

        for doc in docs:
            item = doc.to_dict() or {}

            if (
                cls._normalizar_texto(item.get("data_inicio")) == data_inicio
                and cls._normalizar_texto(item.get("data_fim")) == data_fim
                and cls._normalizar_texto(item.get("unidade_id")) == unidade_id
            ):
                return True

        return False

    @classmethod
    def fechar_caixa(
        cls,
        data_inicio: str,
        data_fim: str,
        unidade_id: str,
        usuario_id: str = "",
        usuario_nome: str = "",
        observacao: str = "",
    ):
        data_inicio = cls._normalizar_texto(data_inicio)
        data_fim = cls._normalizar_texto(data_fim)
        unidade_id = cls._normalizar_texto(unidade_id)
        observacao = cls._normalizar_texto(observacao)

        if not data_inicio:
            return False, "Informe a data inicial para fechar o caixa.", None

        if not data_fim:
            return False, "Informe a data final para fechar o caixa.", None

        if not unidade_id:
            return False, "Selecione uma filial para fechar o caixa.", None

        unidade = cls.buscar_unidade_por_id(unidade_id)

        if not unidade:
            return False, "Filial não encontrada.", None

        if cls.fechamento_ja_existe(data_inicio, data_fim, unidade_id):
            return False, "Já existe um fechamento registrado para esta filial e período.", None

        resultado = cls.gerar_fechamento(
            data_inicio=data_inicio,
            data_fim=data_fim,
            unidade_id=unidade_id,
            forma_pagamento="",
            situacao_pagamento="",
            origem="",
        )

        linhas = resultado.get("linhas") or []
        totais = resultado.get("totais") or {}

        if not linhas:
            return False, "Não existem pedidos para fechar neste período e filial.", None

        agora = cls._agora_iso()
        agora_ord = cls._agora_ord()
        agora_texto = cls._agora_texto()

        pedidos_ids = [item.get("id") for item in linhas]
        pedidos_codigos = [item.get("codigo_pedido") for item in linhas]

        payload = {
            "data_inicio": data_inicio,
            "data_fim": data_fim,

            "unidade_id": unidade_id,
            "unidade_nome": unidade.get("nome", ""),

            "status": "FECHADO",

            "total_pedidos": totais.get("total_pedidos", 0),
            "total_itens": totais.get("total_itens", 0),

            "total_produtos": round(float(totais.get("total_produtos", 0) or 0), 2),
            "total_descontos": round(float(totais.get("total_descontos", 0) or 0), 2),
            "total_entregas": round(float(totais.get("total_entregas", 0) or 0), 2),
            "total_geral": round(float(totais.get("total_geral", 0) or 0), 2),
            "total_pago": round(float(totais.get("total_pago", 0) or 0), 2),
            "total_pendente": round(float(totais.get("total_pendente", 0) or 0), 2),
            "total_cancelado": round(float(totais.get("total_cancelado", 0) or 0), 2),

            "total_geral_formatado": cls._formatar_moeda(totais.get("total_geral", 0)),
            "total_pago_formatado": cls._formatar_moeda(totais.get("total_pago", 0)),
            "total_pendente_formatado": cls._formatar_moeda(totais.get("total_pendente", 0)),
            "total_cancelado_formatado": cls._formatar_moeda(totais.get("total_cancelado", 0)),

            "resumo_por_forma": totais.get("resumo_por_forma", {}),
            "resumo_por_pagamento": totais.get("resumo_por_pagamento", {}),
            "resumo_por_filial": totais.get("resumo_por_filial", {}),
            "resumo_por_origem": totais.get("resumo_por_origem", {}),

            "pedidos_ids": pedidos_ids,
            "pedidos_codigos": pedidos_codigos,

            "observacao": observacao,

            "usuario_id": cls._normalizar_texto(usuario_id),
            "usuario_nome": cls._normalizar_texto(usuario_nome),

            "criado_em": agora,
            "criado_em_ord": agora_ord,
            "criado_em_texto": agora_texto,
        }

        doc_ref = FirebaseService.get_collection(cls.COLECAO_FECHAMENTOS).document()
        doc_ref.set(payload)

        AuditoriaService.registrar_fechamento_caixa(
            fechamento_id=doc_ref.id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            unidade_id=unidade_id,
            unidade_nome=unidade.get("nome", ""),
            usuario_id=usuario_id,
            usuario_nome=usuario_nome,
            totais={
                "total_pedidos": totais.get("total_pedidos", 0),
                "total_itens": totais.get("total_itens", 0),
                "total_produtos": round(float(totais.get("total_produtos", 0) or 0), 2),
                "total_descontos": round(float(totais.get("total_descontos", 0) or 0), 2),
                "total_entregas": round(float(totais.get("total_entregas", 0) or 0), 2),
                "total_geral": round(float(totais.get("total_geral", 0) or 0), 2),
                "total_pago": round(float(totais.get("total_pago", 0) or 0), 2),
                "total_pendente": round(float(totais.get("total_pendente", 0) or 0), 2),
                "total_cancelado": round(float(totais.get("total_cancelado", 0) or 0), 2),
            },
            pedidos_ids=pedidos_ids,
            pedidos_codigos=pedidos_codigos,
        )

        return True, "Caixa fechado com sucesso.", doc_ref.id