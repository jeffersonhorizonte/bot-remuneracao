import os
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
EXCEL_FILE = "04. Farol.xlsx"
COLUNAS = ["Login", "NOME", "Data", "TOTAL"]

# Carrega e valida o Excel
if not os.path.exists(EXCEL_FILE):
    raise FileNotFoundError(f"Arquivo {EXCEL_FILE} não encontrado.")

df = pd.read_excel(EXCEL_FILE)
for col in COLUNAS:
    if col not in df.columns:
        raise ValueError(f"Coluna obrigatória ausente: {col}")
df["Login"] = df["Login"].astype(str).str.replace(r"\D", "", regex=True)

def formatar(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Envie seu CPF para consultar sua remuneração:")

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cpf = update.message.text.replace(".", "").replace("-", "").strip()
    resultado = df[df["Login"] == cpf]

    if resultado.empty:
        await update.message.reply_text("❌ CPF não encontrado.")
        return

    total = resultado["TOTAL"].sum()
    nome = resultado["NOME"].iloc[0]

    resposta = f"🧍 Nome: {nome}\n💰 Total: {formatar(total)}\n\n📅 Detalhamento:\n"
    for _, linha in resultado.iterrows():
        resposta += f"• {linha['Data']}: {formatar(linha['TOTAL'])}\n"

    await update.message.reply_text(resposta)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

if __name__ == "__main__":
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        webhook_url=os.environ.get("WEBHOOK_URL")
    )
