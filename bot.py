
import os
import pandas as pd
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("Erro: Variável de ambiente BOT_TOKEN não encontrada.")
    exit(1)

required_columns = ["Login", "NOME", "DIA", "VR DIÁRIO", "VR TOTAL", "BONIFICAÇÃO", "RESSUPRIMENTO"]

try:
    df = pd.read_excel("04. Farol.xlsx")
    if not all(col in df.columns for col in required_columns):
        raise ValueError("A planilha está com colunas inválidas.")
    df["Login"] = df["Login"].astype(str).str.replace(r'\D', '', regex=True)
except Exception as e:
    print(f"Erro ao carregar a planilha: {e}")
    exit(1)

LOGIN, SENHA = range(2)
usuarios = {}

def fmt(valor):
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
    user_data = usuarios.get(update.effective_user.id, {})
    cpf = user_data.get("cpf")

    if not cpf or not senha:
        await update.message.reply_text("❌ CPF ou senha inválidos.")
        return ConversationHandler.END

    linha = df[df["Login"] == cpf]
    if linha.empty:
        await update.message.reply_text("❌ CPF não encontrado na base.")
    else:
        linha = linha.iloc[0]
        mensagem = (
            f"🧍 Nome: {linha['NOME']}
"
            f"📅 Dia: {linha['DIA']}
"
            f"💰 Valor do dia: {fmt(linha['VR DIÁRIO'])}
"
            f"💸 Valor total: {fmt(linha['VR TOTAL'])}
"
            f"🏆 Bonificação: {fmt(linha['BONIFICAÇÃO'])}
"
            f"📦 Ressuprimento: {fmt(linha['RESSUPRIMENTO'])}"
        )
        await update.message.reply_text(mensagem)

    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Operação cancelada.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()

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
