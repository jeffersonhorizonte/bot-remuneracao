import os
import pandas as pd
import telebot
from flask import Flask, request

API_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

EXCEL_FILE = "04. Farol.xlsx"
COLUNAS_OBRIGATORIAS = ['Login', 'NOME', 'DIA', 'VALOR']

def validar_planilha():
    if not os.path.exists(EXCEL_FILE):
        raise FileNotFoundError(f"Arquivo '{EXCEL_FILE}' não encontrado.")
    df = pd.read_excel(EXCEL_FILE)
    for coluna in COLUNAS_OBRIGATORIAS:
        if coluna not in df.columns:
            raise ValueError(f"Coluna obrigatória '{coluna}' não encontrada na planilha.")
    return df

df = validar_planilha()
df["Login"] = df["Login"].astype(str)

@bot.message_handler(commands=["start"])
def enviar_boas_vindas(message):
    bot.reply_to(message, "Olá! Envie seu CPF para consultar sua remuneração.")

@bot.message_handler(func=lambda msg: True)
def responder_remuneracao(message):
    cpf = message.text.replace(".", "").replace("-", "").strip()
    resultados = df[df["Login"] == cpf]

    if resultados.empty:
        bot.reply_to(message, "❌ CPF não encontrado. Verifique e tente novamente.")
        return

    total = resultados["VALOR"].sum()
    nome = resultados["NOME"].iloc[0]

    mensagem = f"💰 Total recebido: R$ {total:,.2f}\n🧍 Nome: {nome}\n\n📊 Detalhamento:\n"
    for _, linha in resultados.iterrows():
        mensagem += (
            f"📅 Dia: {linha['DIA']} - "
            f"R$ {linha['VALOR']:,.2f}\n"
        )

    bot.reply_to(message, mensagem)

@app.route("/", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ""
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
