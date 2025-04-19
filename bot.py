import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import os

# Carrega a planilha
df = pd.read_excel("04. Farol.xlsx")
df["Login"] = df["Login"].astype(str)

# Formata valores em estilo contábil
def fmt(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Estados da conversa
LOGIN, SENHA = range(2)

# Dicionário de usuários e senhas
usuarios = {
    "12345678900": "senha123",
    "00000000000": "teste",
}

# Início da conversa
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Por favor, digite seu CPF (somente números):")
    return LOGIN

# Recebe o login
async def receber_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cpf = update.message.text.replace(".", "").replace("-", "").strip()
    context.user_data["cpf"] = cpf
    await update.message.reply_text("Agora digite sua senha:")
    return SENHA

# Recebe a senha e retorna dados
async def receber_senha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    senha = update.message.text
    cpf = context.user_data["cpf"]

    if usuarios.get(cpf) == senha:
        dados_usuario = df[df["Login"] == cpf]

        if dados_usuario.empty:
            await update.message.reply_text("Não encontramos seus dados na planilha.")
            return ConversationHandler.END

        linha = dados_usuario.iloc[-1]
        total = dados_usuario["REMUNERAÇÃO VARIÁVEL"].sum()

        resposta = (
            f"📅 Dia: {linha['DIA']}
"
            f"🧍 Nome: {linha['NOME']}
"
            f"💰 Remuneração do dia: {fmt(linha['REMUNERAÇÃO VARIÁVEL'])}
"
            f"📦 Atividade Turno A: {fmt(linha['ATIV. TURNO A'])}
"
            f"📦 Atividade Turno B: {fmt(linha['ATIV. TURNO B'])}
"
            f"💵 Total acumulado: {fmt(total)}"
        )
        await update.message.reply_text(resposta)
    else:
        await update.message.reply_text("CPF ou senha incorretos.")
    return ConversationHandler.END

# Cancela a conversa
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operação cancelada.")
    return ConversationHandler.END

# Inicializa o bot
if __name__ == "__main__":
    TOKEN = os.getenv("BOT_TOKEN")
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
        url_path=os.getenv("BOT_TOKEN"),
        webhook_url=os.getenv("WEBHOOK_URL") + os.getenv("BOT_TOKEN")
    )