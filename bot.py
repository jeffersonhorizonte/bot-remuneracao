from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import pandas as pd
from datetime import datetime
import os

# Carrega a planilha
df = pd.read_excel("04. Farol.xlsx")

# Deixa os CPFs como string (para evitar problemas com zeros à esquerda)
df["CPF"] = df["CPF"].astype(str)

# Estados da conversa
CPF, SENHA = range(2)

# Formata valor como R$ 1.234,56
def fmt(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Por favor, digite seu CPF:")
    return CPF

async def receber_cpf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cpf = update.message.text.replace(".", "").replace("-", "").strip()
    context.user_data["cpf"] = cpf
    await update.message.reply_text("Agora digite sua senha:")
    return SENHA

async def receber_senha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    senha = update.message.text.strip()
    cpf = context.user_data["cpf"]

    linha = df[(df["CPF"] == cpf) & (df["SENHA"] == senha)]

    if not linha.empty:
        linha = linha.iloc[0]
        hoje = datetime.now().day

        mensagem = (
            f"📅 Dia: {linha['DIA']}\n"
            f"- Ativ. Turno A: {fmt(linha['ATIV. TURNO A'])}\n"
            f"- Ativ. Turno B: {fmt(linha['ATIV. TURNO B'])}\n"
            f"- Ressuprimento: {fmt(linha['RESSUPRIMENTO'])}\n\n"
            f"💰 Total acumulado: {fmt(linha['TOTAL'])}"
        )
    else:
        mensagem = "❌ CPF ou senha incorretos. Tente novamente."

    await update.message.reply_text(mensagem)
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operação cancelada.")
    return ConversationHandler.END

if __name__ == "__main__":
    # Carrega o token do ambiente
    TOKEN = os.getenv("TELEGRAM_TOKEN")

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CPF: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_cpf)],
            SENHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_senha)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(conv_handler)

    # Roda com webhook
    async def webhook(request):
        await app.initialize()
        await app.process_update(Update.de_json(await request.json(), app.bot))
        return "OK"

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        webhook_url=os.environ.get("WEBHOOK_URL")
    )
