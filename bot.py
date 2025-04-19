
import os
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
df = pd.read_excel("04. Farol.xlsx")
df["Login"] = df["Login"].astype(str)

LOGIN, SENHA = range(2)
usuarios = {}

def fmt(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Informe seu CPF (apenas números):")
    return LOGIN

async def receber_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cpf = update.message.text.replace(".", "").replace("-", "")
    context.user_data["cpf"] = cpf
    await update.message.reply_text("Agora, digite sua senha:")
    return SENHA

async def receber_senha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    senha = update.message.text
    cpf = context.user_data["cpf"]
    
    linha_usuario = df[df["Login"] == cpf]
    if linha_usuario.empty:
        await update.message.reply_text("CPF não encontrado. Tente novamente com /start")
        return ConversationHandler.END

    linha = linha_usuario.iloc[-1]
    valor_total = df[df["Login"] == cpf]["TOTAL DIA"].sum()

    mensagem = (
        f"🧍 Nome: {linha['NOME']}
"
        f"📅 Dia: {linha['DIA']}
"
        f"💰 Valor do Dia: {fmt(linha['TOTAL DIA'])}
"
        f"📊 Valor Total: {fmt(valor_total)}
"
        f"🔧 Ativ. Turno A: {fmt(linha['ATIV. TURNO A'])}
"
        f"🔩 Ativ. Turno B: {fmt(linha['ATIV. TURNO B'])}"
    )
    await update.message.reply_text(mensagem)
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Consulta cancelada.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_login)],
            SENHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_senha)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    
    app.add_handler(conv_handler)
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        webhook_url=os.environ.get("WEBHOOK_URL")
    )

if __name__ == "__main__":
    main()
