from datetime import datetime
from uuid import uuid4

from werkzeug.security import generate_password_hash, check_password_hash

from services.firebase_service import FirebaseService


class ClienteAuthService:
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
    def buscar_por_id(cls, cliente_id):
        if not cliente_id:
            return None

        doc = cls._collection().document(cliente_id).get()
        if not doc.exists:
            return None

        return cls._normalizar(doc.id, doc.to_dict())

    @classmethod
    def cadastrar(cls, nome, telefone, email, cpf, senha, confirmar_senha):
        nome = (nome or "").strip()
        telefone = (telefone or "").strip()
        email = (email or "").strip().lower()
        cpf = (cpf or "").strip()
        senha = senha or ""
        confirmar_senha = confirmar_senha or ""

        if not nome:
            return False, "Informe o nome.", None

        if not telefone:
            return False, "Informe o telefone.", None

        if not email:
            return False, "Informe o e-mail.", None

        if "@" not in email:
            return False, "Informe um e-mail válido.", None

        if not senha:
            return False, "Informe a senha.", None

        if len(senha) < 6:
            return False, "A senha deve ter no mínimo 6 caracteres.", None

        if senha != confirmar_senha:
            return False, "A confirmação de senha não confere.", None

        existente = cls.buscar_por_email(email)
        if existente:
            return False, "Já existe cadastro com este e-mail.", None

        cliente_id = str(uuid4())
        agora = cls._agora_iso()

        payload = {
            "nome": nome,
            "telefone": telefone,
            "email": email,
            "cpf": cpf,
            "senha_hash": generate_password_hash(senha),
            "ativo": True,
            "origem": "cadastro_site",
            "criado_em": agora,
            "atualizado_em": agora,
        }

        cls._collection().document(cliente_id).set(payload)

        cliente = cls.buscar_por_id(cliente_id)
        return True, "Cadastro realizado com sucesso.", cliente

    @classmethod
    def autenticar(cls, email, senha):
        email = (email or "").strip().lower()
        senha = senha or ""

        if not email:
            return False, "Informe o e-mail.", None

        if not senha:
            return False, "Informe a senha.", None

        cliente = cls.buscar_por_email(email)
        if not cliente:
            return False, "E-mail ou senha inválidos.", None

        if not cliente.get("ativo", True):
            return False, "Seu cadastro está inativo. Entre em contato com o suporte.", None

        senha_hash = cliente.get("senha_hash") or ""
        if not senha_hash or not check_password_hash(senha_hash, senha):
            return False, "E-mail ou senha inválidos.", None

        agora = cls._agora_iso()
        cls._collection().document(cliente["id"]).update({
            "atualizado_em": agora
        })
        cliente["atualizado_em"] = agora

        return True, "Login realizado com sucesso.", cls._normalizar(cliente["id"], cliente)