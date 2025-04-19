import os
import pandas as pd
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
EXCEL_FILE = "04. Farol.xlsx"
INDICADORES = ["EFC", "RESSUPRIMENTO", "EFD", "ATIV. TURNO A", "ATIV. TURNO B", "MONTAGEM", "TMA", "CARREG. AG", "CARREG"]
DESENVOLVIMENTO = ["CICLO DE GENTE", "SKAP - TECNICO", "SKAP - ESPECIFICO", "SAKP - EMPODERAMENTO"]

df = pd.read_excel(EXCEL_FILE)
df["Login"] = df["Login"].astype(str)
df["Senha"] = df["Senha"].astype(str)

LOGIN, SENHA = range(2)
usuarios = {}

def fmt(valor):
    if pd.isna(valor):
        return "N/A"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("👤 Por favor, envie seu CPF (somente números):")
    return LOGIN

async def receber_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cpf = update.message.text.strip().replace(".", "").replace("-", "")
    usuarios[update.effective_user.id] = {"cpf": cpf}
    await update.message.reply_text("🔒 Agora, envie sua senha:")
    return SENHA

async def receber_senha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    senha = update.message.text.strip()
    user_id = update.effective_user.id
    cpf = usuarios.get(user_id, {}).get("cpf")

    if not cpf or not senha:
        await update.message.reply_text("❌ CPF ou senha inválidos.")
        return ConversationHandler.END

    linha = df[(df["Login"] == cpf) & (df["Senha"] == senha)]
    if linha.empty:
        await update.message.reply_text("❌ CPF ou senha incorretos. Tente novamente com /start")
    else:
        linha = linha.iloc[0]
        indicadores = "\n".join([f"• {col}: {fmt(linha[col])}" for col in INDICADORES if col in linha])
        desenvolvimento = "\n".join([f"• {col}: {fmt(linha[col])}" for col in DESENVOLVIMENTO if col in linha])
        mensagem = (
            f"🧍 Nome: {linha['Nome']}\n"
            f"📅 Data: {linha['Data'].strftime('%d/%m')}\n" if not pd.isna(linha['Data']) else ''
            f"🕒 Presença (ABS): {linha['ABS']}\n"
            f"💰 Total do dia: {fmt(linha['TOTAL'])}\n\n"
            f"📊 Indicadores de Desempenho:\n{indicadores}\n\n"
            f"🌱 Desenvolvimento:\n{desenvolvimento}"
        )
        await update.message.reply_text(mensagem)

    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Operação cancelada.", reply_markup=ReplyKeyboardRemove())
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
