import os
import pandas as pd
from flask import Flask, request
import telegram
from telegram import Bot

TOKEN = os.getenv("BOT_TOKEN", "COLE_SEU_TOKEN_AQUI")
bot = Bot(token=TOKEN)

app = Flask(__name__)

# Validação do arquivo
ARQUIVO = "04. Farol.xlsx"
COLUNAS_ESPERADAS = {"Login", "NOME", "DIA", "VALOR"}

if not os.path.exists(ARQUIVO):
    raise FileNotFoundError(f"Arquivo '{ARQUIVO}' não encontrado.")

df = pd.read_excel(ARQUIVO)

colunas_planilha = set(df.columns.str.strip())
if not COLUNAS_ESPERADAS.issubset(colunas_planilha):
    raise ValueError(f"A planilha deve conter as colunas: {COLUNAS_ESPERADAS}. Encontrado: {colunas_planilha}")

df["Login"] = df["Login"].astype(str)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    if update.message and update.message.text:
        cpf = update.message.text.replace(".", "").replace("-", "").strip()
        chat_id = update.message.chat.id

        if not cpf.isdigit():
            bot.send_message(chat_id=chat_id, text="❌ CPF inválido. Digite apenas números.")
            return "ok"

        resultados = df[df["Login"] == cpf]

        if resultados.empty:
            bot.send_message(chat_id=chat_id, text="❌ Nenhuma remuneração encontrada para este CPF.")
        else:
            total = resultados["VALOR"].sum()
            mensagem = f"💰 Total recebido: R$ {total:,.2f}

"
            for _, linha in resultados.iterrows():
                mensagem += (
                    f"🧍 Nome: {linha['NOME']}
"
                    f"📅 Dia: {linha['DIA']}
"
                    f"💵 Valor: R$ {linha['VALOR']:,.2f}

"
                )
            bot.send_message(chat_id=chat_id, text=mensagem)

    return "ok"

@app.route("/", methods=["GET"])
def index():
    return "Bot está rodando com webhook!", 200
