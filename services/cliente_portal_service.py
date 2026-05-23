from datetime import datetime

from services.firebase_service import FirebaseService


class ClientePortalService:
    COLLECTION_NAME = "clientes"

    @classmethod
    def _collection(cls):
        return FirebaseService.get_collection(cls.COLLECTION_NAME)

    @classmethod
    def _agora_iso(cls):
        return datetime.utcnow().isoformat()

    @classmethod
    def _normalizar(cls, doc_id, data):
        data = data or {}
        return {
            "id": doc_id,
            "nome": data.get("nome", ""),
            "telefone": data.get("telefone", ""),
            "email": (data.get("email") or "").strip().lower(),
            "cpf": data.get("cpf", ""),
            "ativo": bool(data.get("ativo", True)),
            "origem": data.get("origem", "cadastro_site"),
            "criado_em": data.get("criado_em"),
            "atualizado_em": data.get("atualizado_em"),
        }

    @classmethod
    def buscar_por_id(cls, cliente_id):
        if not cliente_id:
            return None

        doc = cls._collection().document(cliente_id).get()
        if not doc.exists:
            return None

        return cls._normalizar(doc.id, doc.to_dict())

    @classmethod
    def buscar_por_email(cls, email):
        email = (email or "").strip().lower()
        if not email:
            return None

        docs = cls._collection().where("email", "==", email).limit(1).stream()
        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            return data

        return None

    @classmethod
    def atualizar_cadastro(cls, cliente_id, nome, telefone, email, cpf):
        nome = (nome or "").strip()
        telefone = (telefone or "").strip()
        email = (email or "").strip().lower()
        cpf = (cpf or "").strip()

        if not cliente_id:
            return False, "Cliente inválido.", None

        cliente_atual = cls.buscar_por_id(cliente_id)
        if not cliente_atual:
            return False, "Cliente não encontrado.", None

        if not nome:
            return False, "Informe o nome.", None

        if not telefone:
            return False, "Informe o telefone.", None

        if not email:
            return False, "Informe o e-mail.", None

        if "@" not in email:
            return False, "Informe um e-mail válido.", None

        existente = cls.buscar_por_email(email)
        if existente and existente.get("id") != cliente_id:
            return False, "Este e-mail já está em uso por outro cadastro.", None

        payload = {
            "nome": nome,
            "telefone": telefone,
            "email": email,
            "cpf": cpf,
            "atualizado_em": cls._agora_iso(),
        }

        cls._collection().document(cliente_id).update(payload)

        cliente_atualizado = cls.buscar_por_id(cliente_id)
        return True, "Cadastro atualizado com sucesso.", cliente_atualizado