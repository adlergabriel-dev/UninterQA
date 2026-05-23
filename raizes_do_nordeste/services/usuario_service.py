from datetime import datetime

from services.firebase_service import FirebaseService
from services.firebase_auth_service import FirebaseAuthService


class UsuarioService:
    COLECAO = "usuarios"
    PERFIS_VALIDOS = ["ADMIN", "GERENTE", "USUARIO"]

    @classmethod
    def listar(cls):
        docs = FirebaseService.get_collection(cls.COLECAO).stream()
        resultado = []

        for doc in docs:
            item = doc.to_dict() or {}

            # ID REAL do documento no Firestore.
            # Este é o campo correto para editar, ativar e inativar.
            item["doc_id"] = doc.id

            # Mantém também id por compatibilidade com telas antigas.
            item["id"] = doc.id

            # UID do Firebase Auth.
            # Se não existir no documento, tenta usar o doc.id como fallback.
            if not item.get("uid"):
                item["uid"] = doc.id

            resultado.append(item)

        resultado.sort(key=lambda x: (x.get("nome") or "").lower())
        return resultado

    @classmethod
    def buscar_por_id(cls, usuario_id: str):
        usuario_id = (usuario_id or "").strip()

        if not usuario_id:
            return None

        doc_ref = FirebaseService.get_collection(cls.COLECAO).document(usuario_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict() or {}

        data["doc_id"] = doc.id
        data["id"] = doc.id

        if not data.get("uid"):
            data["uid"] = doc.id

        return data

    @classmethod
    def buscar_por_email(cls, email: str, ignorar_id: str = None):
        email = (email or "").strip().lower()
        ignorar_id = (ignorar_id or "").strip() if ignorar_id else None

        if not email:
            return None

        docs = (
            FirebaseService.get_collection(cls.COLECAO)
            .where("email", "==", email)
            .stream()
        )

        for doc in docs:
            if ignorar_id and doc.id == ignorar_id:
                continue

            data = doc.to_dict() or {}
            data["doc_id"] = doc.id
            data["id"] = doc.id

            if not data.get("uid"):
                data["uid"] = doc.id

            return data

        return None

    @classmethod
    def validar_dados(cls, dados: dict, ignorar_id: str = None, criando: bool = False):
        nome = (dados.get("nome") or "").strip()
        email = (dados.get("email") or "").strip().lower()
        perfil = (dados.get("perfil") or "").strip().upper()
        senha = (dados.get("senha") or "").strip()
        confirmar_senha = (dados.get("confirmar_senha") or "").strip()

        if not nome:
            raise ValueError("O nome é obrigatório.")

        if not email:
            raise ValueError("O e-mail é obrigatório.")

        if "@" not in email:
            raise ValueError("Informe um e-mail válido.")

        if not perfil:
            raise ValueError("O perfil é obrigatório.")

        if perfil not in cls.PERFIS_VALIDOS:
            raise ValueError("Perfil inválido.")

        existente = cls.buscar_por_email(email, ignorar_id=ignorar_id)
        if existente:
            raise ValueError("Já existe um usuário com este e-mail.")

        if criando:
            if not senha:
                raise ValueError("A senha inicial é obrigatória.")

            if len(senha) < 6:
                raise ValueError("A senha deve ter pelo menos 6 caracteres.")

            if senha != confirmar_senha:
                raise ValueError("A confirmação de senha não confere.")
        else:
            if senha or confirmar_senha:
                if len(senha) < 6:
                    raise ValueError("A nova senha deve ter pelo menos 6 caracteres.")

                if senha != confirmar_senha:
                    raise ValueError("A confirmação da nova senha não confere.")

    @classmethod
    def criar(cls, dados: dict):
        cls.validar_dados(dados, criando=True)

        nome = (dados.get("nome") or "").strip()
        email = (dados.get("email") or "").strip().lower()
        perfil = (dados.get("perfil") or "").strip().upper()
        senha = (dados.get("senha") or "").strip()

        agora = datetime.utcnow().isoformat()
        auth_service = FirebaseAuthService()

        usuario_auth = auth_service.criar_usuario(
            email=email,
            senha=senha,
            nome=nome,
        )

        uid = usuario_auth.uid

        payload = {
            "nome": nome,
            "email": email,
            "perfil": perfil,
            "uid": uid,
            "ativo": True,
            "criado_em": agora,
            "atualizado_em": agora,
        }

        try:
            FirebaseService.get_collection(cls.COLECAO).document(uid).set(payload)

        except Exception:
            try:
                auth_service.excluir_usuario(uid)
            except Exception:
                pass

            raise

        return uid

    @classmethod
    def atualizar(cls, usuario_id: str, dados: dict):
        usuario_id = (usuario_id or "").strip()

        usuario = cls.buscar_por_id(usuario_id)
        if not usuario:
            raise ValueError("Usuário não encontrado.")

        cls.validar_dados(dados, ignorar_id=usuario_id, criando=False)

        nome = (dados.get("nome") or "").strip()
        email = (dados.get("email") or "").strip().lower()
        perfil = (dados.get("perfil") or "").strip().upper()
        senha = (dados.get("senha") or "").strip()

        uid = (usuario.get("uid") or usuario_id or "").strip()

        if not uid:
            raise ValueError("UID Firebase Auth não encontrado para este usuário.")

        auth_service = FirebaseAuthService()

        auth_service.atualizar_usuario(
            uid=uid,
            email=email,
            nome=nome,
            senha=senha if senha else None,
            ativo=usuario.get("ativo", True),
        )

        payload = {
            "nome": nome,
            "email": email,
            "perfil": perfil,
            "uid": uid,
            "atualizado_em": datetime.utcnow().isoformat(),
        }

        FirebaseService.get_collection(cls.COLECAO).document(usuario_id).update(payload)

    @classmethod
    def alterar_status(cls, usuario_id: str, ativo: bool):
        usuario_id = (usuario_id or "").strip()

        usuario = cls.buscar_por_id(usuario_id)
        if not usuario:
            raise ValueError("Usuário não encontrado.")

        uid = (usuario.get("uid") or usuario_id or "").strip()

        if not uid:
            raise ValueError("UID Firebase Auth não encontrado para este usuário.")

        auth_service = FirebaseAuthService()
        auth_service.definir_status_usuario(uid, ativo)

        FirebaseService.get_collection(cls.COLECAO).document(usuario_id).update({
            "ativo": ativo,
            "uid": uid,
            "atualizado_em": datetime.utcnow().isoformat(),
        })