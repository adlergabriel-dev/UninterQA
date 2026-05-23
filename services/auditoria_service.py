from datetime import datetime
from typing import Optional, Dict, Any, List

from services.firebase_service import FirebaseService


class AuditoriaService:
    COLECAO = "auditoria"

    ORIGEM_WEB = "WEB"
    ORIGEM_CLIENTE = "CLIENTE"
    ORIGEM_INTERNO = "INTERNO"
    ORIGEM_SISTEMA = "SISTEMA"

    ENTIDADE_PEDIDO = "PEDIDO"
    ENTIDADE_CLIENTE = "CLIENTE"
    ENTIDADE_PRODUTO = "PRODUTO"
    ENTIDADE_UNIDADE = "UNIDADE"
    ENTIDADE_CARDAPIO = "CARDAPIO"
    ENTIDADE_USUARIO = "USUARIO"
    ENTIDADE_PAGAMENTO = "PAGAMENTO"
    ENTIDADE_FECHAMENTO_CAIXA = "FECHAMENTO_CAIXA"

    ACAO_CRIAR = "CRIAR"
    ACAO_EDITAR = "EDITAR"
    ACAO_EXCLUIR = "EXCLUIR"
    ACAO_CANCELAR = "CANCELAR"
    ACAO_STATUS = "ALTERAR_STATUS"
    ACAO_PAGAMENTO = "ALTERAR_PAGAMENTO"
    ACAO_LOGIN = "LOGIN"
    ACAO_LOGOUT = "LOGOUT"
    ACAO_FECHAR_CAIXA = "FECHAR_CAIXA"

    @classmethod
    def _collection(cls):
        return FirebaseService.get_collection(cls.COLECAO)

    @classmethod
    def _texto(cls, valor) -> str:
        return str(valor or "").strip()

    @classmethod
    def _upper(cls, valor) -> str:
        return cls._texto(valor).upper()

    @classmethod
    def _agora_iso(cls) -> str:
        return datetime.utcnow().isoformat()

    @classmethod
    def _agora_ord(cls) -> str:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def _agora_texto(cls) -> str:
        return datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")

    @classmethod
    def _limpar_dict(cls, dados):
        if not dados:
            return {}

        if not isinstance(dados, dict):
            return {}

        retorno = {}

        for chave, valor in dados.items():
            chave_limpa = cls._texto(chave)

            if not chave_limpa:
                continue

            if isinstance(valor, (str, int, float, bool)) or valor is None:
                retorno[chave_limpa] = valor

            elif isinstance(valor, list):
                retorno[chave_limpa] = valor

            elif isinstance(valor, dict):
                retorno[chave_limpa] = valor

            else:
                retorno[chave_limpa] = str(valor)

        return retorno

    @classmethod
    def registrar(
        cls,
        entidade: str,
        entidade_id: str,
        acao: str,
        descricao: str,
        origem: str = "WEB",
        usuario_id: str = "",
        usuario_nome: str = "",
        dados_antes: Optional[Dict[str, Any]] = None,
        dados_depois: Optional[Dict[str, Any]] = None,
        metadados: Optional[Dict[str, Any]] = None,
    ) -> str:
        agora_iso = cls._agora_iso()
        agora_ord = cls._agora_ord()
        agora_texto = cls._agora_texto()

        payload = {
            "entidade": cls._upper(entidade),
            "entidade_id": cls._texto(entidade_id),
            "acao": cls._upper(acao),
            "descricao": cls._texto(descricao),
            "origem": cls._upper(origem or cls.ORIGEM_WEB),

            "usuario_id": cls._texto(usuario_id),
            "usuario_nome": cls._texto(usuario_nome),

            "dados_antes": cls._limpar_dict(dados_antes),
            "dados_depois": cls._limpar_dict(dados_depois),
            "metadados": cls._limpar_dict(metadados),

            "criado_em": agora_iso,
            "criado_em_ord": agora_ord,
            "criado_em_texto": agora_texto,
        }

        doc_ref = cls._collection().document()
        doc_ref.set(payload)

        return doc_ref.id

    @classmethod
    def registrar_pedido(
        cls,
        pedido_id: str,
        codigo_pedido: str = "",
        acao: str = "",
        descricao: str = "",
        origem: str = "INTERNO",
        usuario_id: str = "",
        usuario_nome: str = "",
        status_anterior: str = "",
        status_novo: str = "",
        pagamento_anterior: str = "",
        pagamento_novo: str = "",
        dados_antes: Optional[Dict[str, Any]] = None,
        dados_depois: Optional[Dict[str, Any]] = None,
    ) -> str:
        metadados = {
            "codigo_pedido": cls._texto(codigo_pedido),
            "status_anterior": cls._upper(status_anterior),
            "status_novo": cls._upper(status_novo),
            "pagamento_anterior": cls._upper(pagamento_anterior),
            "pagamento_novo": cls._upper(pagamento_novo),
        }

        return cls.registrar(
            entidade=cls.ENTIDADE_PEDIDO,
            entidade_id=pedido_id,
            acao=acao,
            descricao=descricao,
            origem=origem,
            usuario_id=usuario_id,
            usuario_nome=usuario_nome,
            dados_antes=dados_antes,
            dados_depois=dados_depois,
            metadados=metadados,
        )

    @classmethod
    def registrar_pagamento(
        cls,
        pedido_id: str,
        codigo_pedido: str = "",
        pagamento_anterior: str = "",
        pagamento_novo: str = "",
        usuario_id: str = "",
        usuario_nome: str = "",
        origem: str = "INTERNO",
    ) -> str:
        descricao = (
            f"Pagamento do pedido {codigo_pedido or pedido_id} alterado "
            f"de {pagamento_anterior or '-'} para {pagamento_novo or '-'}."
        )

        return cls.registrar_pedido(
            pedido_id=pedido_id,
            codigo_pedido=codigo_pedido,
            acao=cls.ACAO_PAGAMENTO,
            descricao=descricao,
            origem=origem,
            usuario_id=usuario_id,
            usuario_nome=usuario_nome,
            pagamento_anterior=pagamento_anterior,
            pagamento_novo=pagamento_novo,
            dados_antes={
                "pagamento_status": pagamento_anterior,
            },
            dados_depois={
                "pagamento_status": pagamento_novo,
            },
        )

    @classmethod
    def registrar_status_pedido(
        cls,
        pedido_id: str,
        codigo_pedido: str = "",
        status_anterior: str = "",
        status_novo: str = "",
        usuario_id: str = "",
        usuario_nome: str = "",
        origem: str = "INTERNO",
    ) -> str:
        descricao = (
            f"Status do pedido {codigo_pedido or pedido_id} alterado "
            f"de {status_anterior or '-'} para {status_novo or '-'}."
        )

        acao = cls.ACAO_CANCELAR if cls._upper(status_novo) == "CANCELADO" else cls.ACAO_STATUS

        return cls.registrar_pedido(
            pedido_id=pedido_id,
            codigo_pedido=codigo_pedido,
            acao=acao,
            descricao=descricao,
            origem=origem,
            usuario_id=usuario_id,
            usuario_nome=usuario_nome,
            status_anterior=status_anterior,
            status_novo=status_novo,
            dados_antes={
                "status": status_anterior,
            },
            dados_depois={
                "status": status_novo,
            },
        )

    @classmethod
    def registrar_fechamento_caixa(
        cls,
        fechamento_id: str,
        data_inicio: str,
        data_fim: str,
        unidade_id: str,
        unidade_nome: str,
        usuario_id: str = "",
        usuario_nome: str = "",
        totais: Optional[Dict[str, Any]] = None,
        pedidos_ids: Optional[List[str]] = None,
        pedidos_codigos: Optional[List[str]] = None,
    ) -> str:
        totais = totais or {}
        pedidos_ids = pedidos_ids or []
        pedidos_codigos = pedidos_codigos or []

        descricao = (
            f"Fechamento de caixa registrado para a filial {unidade_nome or unidade_id}, "
            f"período {data_inicio or '-'} até {data_fim or '-'}."
        )

        dados_depois = {
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "unidade_id": unidade_id,
            "unidade_nome": unidade_nome,
            "total_pedidos": totais.get("total_pedidos", 0),
            "total_itens": totais.get("total_itens", 0),
            "total_produtos": totais.get("total_produtos", 0),
            "total_descontos": totais.get("total_descontos", 0),
            "total_entregas": totais.get("total_entregas", 0),
            "total_geral": totais.get("total_geral", 0),
            "total_pago": totais.get("total_pago", 0),
            "total_pendente": totais.get("total_pendente", 0),
            "total_cancelado": totais.get("total_cancelado", 0),
        }

        metadados = {
            "fechamento_id": fechamento_id,
            "pedidos_ids": pedidos_ids,
            "pedidos_codigos": pedidos_codigos,
        }

        return cls.registrar(
            entidade=cls.ENTIDADE_FECHAMENTO_CAIXA,
            entidade_id=fechamento_id,
            acao=cls.ACAO_FECHAR_CAIXA,
            descricao=descricao,
            origem=cls.ORIGEM_INTERNO,
            usuario_id=usuario_id,
            usuario_nome=usuario_nome,
            dados_antes={},
            dados_depois=dados_depois,
            metadados=metadados,
        )

    @classmethod
    def listar(cls, limite: int = 300) -> List[Dict[str, Any]]:
        docs = cls._collection().stream()
        resultado = []

        for doc in docs:
            item = doc.to_dict() or {}
            item["id"] = doc.id

            if not item.get("criado_em_texto"):
                item["criado_em_texto"] = cls._formatar_data_para_tela(item.get("criado_em"))

            resultado.append(item)

        resultado.sort(
            key=lambda x: x.get("criado_em_ord") or x.get("criado_em") or "",
            reverse=True
        )

        if limite and limite > 0:
            return resultado[:limite]

        return resultado

    @classmethod
    def listar_filtrado(
        cls,
        entidade: str = "",
        acao: str = "",
        usuario_nome: str = "",
        origem: str = "",
        limite: int = 300,
    ) -> List[Dict[str, Any]]:
        entidade = cls._upper(entidade)
        acao = cls._upper(acao)
        usuario_nome = cls._texto(usuario_nome).lower()
        origem = cls._upper(origem)

        eventos = cls.listar(limite=0)
        filtrados = []

        for item in eventos:
            if entidade and cls._upper(item.get("entidade")) != entidade:
                continue

            if acao and cls._upper(item.get("acao")) != acao:
                continue

            if origem and cls._upper(item.get("origem")) != origem:
                continue

            if usuario_nome and usuario_nome not in cls._texto(item.get("usuario_nome")).lower():
                continue

            filtrados.append(item)

        if limite and limite > 0:
            return filtrados[:limite]

        return filtrados

    @classmethod
    def _formatar_data_para_tela(cls, valor):
        if not valor:
            return "-"

        if isinstance(valor, datetime):
            return valor.strftime("%d/%m/%Y %H:%M:%S")

        valor = cls._texto(valor)

        formatos = [
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
        ]

        for formato in formatos:
            try:
                return datetime.strptime(valor[:26], formato).strftime("%d/%m/%Y %H:%M:%S")
            except Exception:
                pass

        return valor