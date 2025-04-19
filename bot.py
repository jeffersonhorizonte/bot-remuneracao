
import os
import pandas as pd
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

app = Flask(__name__)

df = pd.read_excel("04. Farol.xlsx")
df["Login"] = df["Login"].astype(str)

USERS = {}

LOGIN, SENHA = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Digite seu CPF (somente números):")
    return LOGIN

async def receber_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cpf = update.message.text.replace(".", "").replace("-", "")
    context.user_data["cpf"] = cpf
    await update.message.reply_text("Agora digite sua senha:")
    return SENHA

async def receber_senha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    senha = update.message.text
    cpf = context.user_data["cpf"]

    # Verificação simples de senha
    if senha != "1234":
        await update.message.reply_text("Senha incorreta.")
        return ConversationHandler.END

    colaborador = df[df["Login"] == cpf]

    if colaborador.empty:
        await update.message.reply_text("CPF não encontrado.")
        return ConversationHandler.END

    linha = colaborador.iloc[-1]
    total = colaborador["REMUNERAÇÃO VARIÁVEL"].sum()

    def fmt(valor):
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    mensagem = (
        f"🧍 Nome: {linha['NOME']}
"
        f"📅 Dia: {linha['DIA']}
"
        f"💰 Valor do dia: {fmt(linha['REMUNERAÇÃO VARIÁVEL'])}
"
        f"📊 Total acumulado: {fmt(total)}
"
        f"📌 Ativ. Turno A: {fmt(linha['ATIV. TURNO A'])}
"
        f"📌 Ativ. Turno B: {fmt(linha['ATIV. TURNO B'])}"
    )

    await update.message.reply_text(mensagem)
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operação cancelada.")
    return ConversationHandler.END

application = ApplicationBuilder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_login)],
        SENHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_senha)],
    },
    fallbacks=[CommandHandler("cancelar", cancelar)],
)

application.add_handler(conv_handler)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put_nowait(update)
    return "ok"

@app.route("/")
def index():
    return "Bot está no ar!"

if __name__ == "__main__":
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        url_path=TOKEN,
        webhook_url=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    )
