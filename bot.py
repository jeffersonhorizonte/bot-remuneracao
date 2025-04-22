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

    resultados = df[(df["Login"] == cpf) & (df["Senha"] == senha)]
    if resultados.empty:
        await update.message.reply_text("⚠️ Opa, algo está incorreto. Verifique se o CPF está sem pontos ou traços, ou se a senha que você digitou é a correta.")
    else:
        detalhes = ""
        total_geral = resultados["TOTAL"].sum()
        for _, dia in resultados.iterrows():
            data_fmt = dia["Data"].strftime("%d/%m") if not pd.isna(dia["Data"]) else "-"
            abs_valor = dia["ABS"]
            valor_dia = fmt(dia["TOTAL"])
            detalhes += f"• {data_fmt} - ABS: {abs_valor} - Total: {valor_dia}\n"

        resultados_filtrados = resultados[resultados["Data"] < pd.Timestamp.now().normalize()]
        if resultados_filtrados.empty:
            ult = resultados.iloc[-1]
        else:
            ult = resultados_filtrados.iloc[-1]
        indicadores = "\n".join([f"• {col}: {fmt(ult[col])}" for col in INDICADORES if col in ult])
        desenvolvimento = "\n".join([
            f"• {col}: {int(ult[col]*100)}%" if 'SKAP' in col or 'SAKP' in col else f"• {col}: {ult[col]}"
            for col in DESENVOLVIMENTO if col in ult])

        mensagem = (
            f"🧍 Nome: {ult['Nome']}\n"
            f"💰 Total recebido no período: {fmt(total_geral)}\n\n"
            f"📅 Detalhamento por dia:\n{detalhes}\n"
            f"📊 Indicadores de Desempenho (referente a {ult['Data'].strftime('%d/%m')}):\n{indicadores}\n\n"
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
