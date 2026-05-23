import firebase_admin
from firebase_admin import auth as firebase_auth
from services.firebase_service import FirebaseService


class FirebaseAuthService:
    def __init__(self):
        FirebaseService.inicializar()

        try:
            self.app = firebase_admin.get_app()
        except ValueError:
            self.app = None

    def criar_usuario(self, email: str, senha: str, nome: str = ""):
        try:
            return firebase_auth.create_user(
                email=(email or "").strip().lower(),
                password=senha,
                display_name=(nome or "").strip() or None,
                disabled=False,
            )
        except firebase_auth.EmailAlreadyExistsError:
            raise ValueError("Já existe um usuário no Firebase Authentication com este e-mail.")
        except Exception as e:
            raise ValueError(f"Erro ao criar usuário no Firebase Authentication: {str(e)}")

    def atualizar_usuario(self, uid: str, email: str = None, nome: str = None, senha: str = None, ativo: bool = True):
        if not uid:
            raise ValueError("UID do Firebase Authentication não informado.")

        kwargs = {
            "disabled": not bool(ativo)
        }

        if email is not None and str(email).strip():
            kwargs["email"] = str(email).strip().lower()

        if nome is not None:
            nome = str(nome).strip()
            kwargs["display_name"] = nome if nome else None

        if senha is not None and str(senha).strip():
            kwargs["password"] = str(senha).strip()

        try:
            return firebase_auth.update_user(uid, **kwargs)
        except firebase_auth.EmailAlreadyExistsError:
            raise ValueError("Já existe um usuário no Firebase Authentication com este e-mail.")
        except firebase_auth.UserNotFoundError:
            raise ValueError("Usuário não encontrado no Firebase Authentication.")
        except Exception as e:
            raise ValueError(f"Erro ao atualizar usuário no Firebase Authentication: {str(e)}")

    def definir_status_usuario(self, uid: str, ativo: bool):
        if not uid:
            raise ValueError("UID do Firebase Authentication não informado.")

        try:
            return firebase_auth.update_user(uid, disabled=not bool(ativo))
        except firebase_auth.UserNotFoundError:
            raise ValueError("Usuário não encontrado no Firebase Authentication.")
        except Exception as e:
            raise ValueError(f"Erro ao alterar status no Firebase Authentication: {str(e)}")

    def excluir_usuario(self, uid: str):
        if not uid:
            return

        try:
            firebase_auth.delete_user(uid)
        except Exception:
            pass