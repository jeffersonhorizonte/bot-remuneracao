
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters
import os

# Carregar dados
required_columns = [
    "Login", "Senha", "NOME", "DIA", "TOTAL GERAL", "RESSUPRIMENTO",
    "ATIV. TURNO A", "ATIV. TURNO B"
]

df = pd.read_excel("04. Farol.xlsx")
if not all(col in df.columns for col in required_columns):
    missing = [col for col in required_columns if col not in df.columns]
    raise ValueError(f"Colunas ausentes no Excel: {', '.join(missing)}")

df["Login"] = df["Login"].astype(str)
df["Senha"] = df["Senha"].astype(str)

LOGIN, SENHA = range(2)
usuarios_temp = {}

def fmt(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bem-vindo! Digite seu CPF para login:")
    return LOGIN

async def receber_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cpf = update.message.text.replace(".", "").replace("-", "").strip()
    usuarios_temp[update.effective_user.id] = {"cpf": cpf}
    await update.message.reply_text("Agora digite sua senha:")
    return SENHA

async def receber_senha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    senha = update.message.text.strip()
    user_id = update.effective_user.id
    cpf = usuarios_temp[user_id]["cpf"]
    linha = df[(df["Login"] == cpf) & (df["Senha"] == senha)]

    if not linha.empty:
        linha = linha.iloc[0]
        mensagem = (
            f"🧍 Nome: {linha['NOME']}
"
            f"📅 Dia: {linha['DIA']}
"
            f"💰 Total Geral: {fmt(linha['TOTAL GERAL'])}
"
            f"📦 Ressuprimento: {fmt(linha['RESSUPRIMENTO'])}
"
            f"✅ Ativ. Turno A: {fmt(linha['ATIV. TURNO A'])}
"
            f"✅ Ativ. Turno B: {fmt(linha['ATIV. TURNO B'])}"
        )
        await update.message.reply_text(mensagem)
    else:
        await update.message.reply_text("Login ou senha incorretos. Tente novamente com /start")

    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operação cancelada.")
    return ConversationHandler.END

app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_login)],
        SENHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_senha)],
    },
    fallbacks=[CommandHandler("cancelar", cancelar)],
)

app.add_handler(conv_handler)

if __name__ == "__main__":
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        webhook_url=os.environ.get("WEBHOOK_URL")
    )
