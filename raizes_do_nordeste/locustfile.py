from locust import HttpUser, task, between
from locust.exception import StopUser
import random


UNIDADE_ID = "QKdXJiw2gD5j14kwVyo"

# Troque pelo ID real do produto sopa
PRODUTO_ID_SOPA = "SOPA"


class ClientePedidoUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.cliente_teste = f"Cliente Teste {random.randint(1, 999999)}"

    @task
    def criar_um_pedido_sopa_e_parar(self):
        # Abre a tela do pedido
        self.client.get(
            f"/cliente/pedido/novo?unidade_id={UNIDADE_ID}",
            name="Abrir tela Novo Pedido"
        )

        dados = {
            "forma_pagamento": "PIX",
            f"quantidade_{PRODUTO_ID_SOPA}": "1",
            f"observacao_{PRODUTO_ID_SOPA}": "Teste automático de carga - sopa"
        }

        resposta = self.client.post(
            f"/cliente/pedido/novo?unidade_id={UNIDADE_ID}",
            data=dados,
            name="Criar Pedido Sopa",
            allow_redirects=True
        )

        if resposta.status_code not in [200, 302]:
            print("Erro ao criar pedido:", resposta.status_code, resposta.text[:300])

        # Para o usuário virtual após criar 1 pedido
        raise StopUser()