
import logging
import os
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
EXCEL_FILE = "04. Farol.xlsx"
COLUNAS_OBRIGATORIAS = [
    "Login", "SENHA", "NOME", "DIA", "TOTAL", 
    "RESSUPRIMENTO", "ATIV. TURNO A", "ATIV. TURNO B"
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOGIN, SENHA = range(2)

def formatar_valor(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Olá! Digite seu CPF (apenas números):")
    return LOGIN

async def receber_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["login"] = update.message.text.replace(".", "").replace("-", "")
    await update.message.reply_text("🔐 Agora, digite sua senha:")
    return SENHA

async def receber_senha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    senha = update.message.text
    login = context.user_data["login"]

    if not os.path.exists(EXCEL_FILE):
        await update.message.reply_text("❌ Arquivo Excel não encontrado no servidor.")
        return ConversationHandler.END

    try:
        df = pd.read_excel(EXCEL_FILE)
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao ler a planilha: {e}")
        return ConversationHandler.END

    colunas_faltando = [col for col in COLUNAS_OBRIGATORIAS if col not in df.columns]
    if colunas_faltando:
        await update.message.reply_text(f"❌ Colunas ausentes no Excel: {', '.join(colunas_faltando)}")
        return ConversationHandler.END

    df["Login"] = df["Login"].astype(str).str.replace(".", "").str.replace("-", "")
    usuario = df[(df["Login"] == login) & (df["SENHA"].astype(str) == senha)]

    if usuario.empty:
        await update.message.reply_text("❌ CPF ou senha incorretos.")
    else:
        linha = usuario.iloc[0]
        resposta = (
            f"🧍 Nome: {linha['NOME']}
"
            f"📅 Dia: {linha['DIA']}
"
            f"💰 Total: {formatar_valor(linha['TOTAL'])}
"
            f"📦 Ressuprimento: {formatar_valor(linha['RESSUPRIMENTO'])}
"
            f"✅ Atividades Turno A: {formatar_valor(linha['ATIV. TURNO A'])}
"
            f"✅ Atividades Turno B: {formatar_valor(linha['ATIV. TURNO B'])}"
        )
        await update.message.reply_text(resposta)

    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operação cancelada.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_login)],
            SENHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_senha)],
        },
        fallbacks=[CommandHandler("cancel", cancelar)],
    )

    app.add_handler(conv_handler)
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        webhook_url=os.environ.get("RENDER_EXTERNAL_URL") + "/"
    )

if __name__ == "__main__":
    main()
