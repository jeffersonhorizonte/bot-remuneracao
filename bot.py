
import os
import pandas as pd
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
app = Flask(__name__)

# Carregar a planilha
df = pd.read_excel("04. Farol.xlsx")
df["Login"] = df["Login"].astype(str)

# Estados da conversa
CPF, SENHA = range(2)

# Senhas simuladas (substituir pelo seu controle real)
senhas = {"12345678900": "senha123", "98765432100": "teste456"}

def fmt(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Por favor, envie seu CPF para continuar:")
    return CPF

async def receber_cpf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cpf = update.message.text.replace(".", "").replace("-", "")
    context.user_data["cpf"] = cpf
    await update.message.reply_text("Agora, envie sua senha:")
    return SENHA

async def receber_senha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    senha = update.message.text
    cpf = context.user_data["cpf"]
    if cpf in senhas and senhas[cpf] == senha:
        dados = df[df["Login"] == cpf]
        if dados.empty:
            await update.message.reply_text("Nenhum dado encontrado para este CPF.")
        else:
            linha = dados.iloc[-1]
            total = dados["R$"].sum()
            await update.message.reply_text(
                f"🧍 Nome: {linha['NOME']}
"
                f"📅 Dia: {linha['DIA']}
"
                f"💰 Valor do dia: {fmt(linha['R$'])}
"
                f"📊 Atividade Turno A: {linha['ATIV. TURNO A']}
"
                f"📊 Atividade Turno B: {linha['ATIV. TURNO B']}
"
                f"💵 Total acumulado: {fmt(total)}"
            )
    else:
        await update.message.reply_text("CPF ou senha inválidos. Tente novamente.")
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operação cancelada.")
    return ConversationHandler.END

application = Application.builder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        CPF: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_cpf)],
        SENHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_senha)],
    },
    fallbacks=[CommandHandler("cancelar", cancelar)],
)

application.add_handler(conv_handler)

@app.route("/", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put_nowait(update)
    return "ok"

if __name__ == "__main__":
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        url_path=TOKEN,
        webhook_url=f"https://bot-remuneracao.onrender.com/{TOKEN}"
    )
