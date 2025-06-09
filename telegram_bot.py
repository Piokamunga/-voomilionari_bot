import requests

# --- Configuração ---
TOKEN = "7585234067:AAF1xfSbMCh7LOckXViD2_iUfKig7GYgwO4"
PRIVATE_CHAT_ID = 8101413562
GROUP_CHAT_ID = int(os.getenv("GRUPO_ID", "-1002769928832"))  # fallback caso variável não esteja setada

# ✅ Ativar ou desativar modo de teste
modo_teste = True


def send_message(text, chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print(f"Mensagem enviada para {chat_id}: {text}")
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")


def executar_teste_envio():
    print("🔍 Executando testes de envio...")
    send_message("✅ <b>Teste de envio privado</b> realizado com sucesso!", PRIVATE_CHAT_ID)
    send_message("📢 <b>Teste de envio no grupo VOO MILIONÁRIO</b> realizado com sucesso!", GROUP_CHAT_ID)


if __name__ == "__main__":
    if modo_teste:
        executar_teste_envio()
    else:
        print("⚙️ Bot em modo produção (sem testes)")
