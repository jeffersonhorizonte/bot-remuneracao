
import os
import pandas as pd
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.ext import ConversationHandler
import logging

# Carregar token do bot do ambiente
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

# Configuração do Flask
app = Flask(__name__)

# Configurar logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# Estados da conversa
CPF, SENHA = range(2)

# Carregar a planilha
df = pd.read_excel("04. Farol.xlsx")
df['CPF'] = df['CPF'].astype(str).str.replace(r'\D', '', regex=True)

# Formatar valor contábil
def fmt(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Início da conversa
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Digite seu CPF para consultar sua remuneração variável:")
    return CPF

async def receber_cpf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cpf = update.message.text.strip().replace(".", "").replace("-", "")
    context.user_data["cpf"] = cpf
    await update.message.reply_text("Agora digite sua senha:")
    return SENHA

async def receber_senha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    senha = update.message.text.strip()
    cpf = context.user_data["cpf"]

    # Filtra pelo CPF
    linha = df[df["CPF"] == cpf]

    if linha.empty:
        await update.message.reply_text("CPF não encontrado.")
        return ConversationHandler.END

    if str(linha["SENHA"].values[0]) != senha:
        await update.message.reply_text("Senha incorreta.")
        return ConversationHandler.END

    # Extrai os dados
    linha = linha.iloc[0]
    msg = (
        f"📅 Dia: {linha['DIA']}
"
        f"💰 Valor do Dia: {fmt(linha['VALOR DIA'])}
"
        f"💰 Total: {fmt(linha['TOTAL'])}

"
        f"🔧 Ativ. Turno A: {linha['ATIV. TURNO A']}
"
        f"🔧 Ativ. Turno B: {linha['ATIV. TURNO B']}"
    )
    await update.message.reply_text(msg)
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Consulta cancelada.")
    return ConversationHandler.END

# Setup do Telegram
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

# Rota para Webhook
@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    await application.process_update(update)
    return "ok"

# Rota simples para testar se está online
@app.route("/", methods=["GET"])
def home():
    return "Bot está online!"

# Iniciar app Flask
if __name__ == "__main__":
    app.run(debug=True, port=5000)
