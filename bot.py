import os
import pandas as pd
from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
EXCEL_FILE = "04. Farol.xlsx"
INDICADORES = ["EFC", "RESSUPRIMENTO", "EFD", "ATIV. TURNO A", "ATIV. TURNO B", "MONTAGEM", "TMA", "CARREG. AG", "CARREG"]
DESENVOLVIMENTO = ["CICLO DE GENTE", "SKAP - TECNICO", "SKAP - ESPECIFICO", "SAKP - EMPODERAMENTO"]

df = pd.read_excel(EXCEL_FILE)
df["Login"] = df["Login"].astype(str)
df["Senha"] = df["Senha"].astype(str)

LOGIN, SENHA, SELECIONAR_MES = range(3)
usuarios = {}

def fmt(valor):
    if pd.isna(valor):
        return "N/A"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("👤 Por favor, envie seu CPF (somente números):")
    context.user_data["conversation"] = LOGIN
    return LOGIN

async def receber_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cpf = update.message.text.strip().replace(".", "").replace("-", "")
    usuarios[update.effective_user.id] = {"cpf": cpf}
    await update.message.reply_text("🔒 Agora, envie sua senha:")
    context.user_data["conversation"] = SENHA
    return SENHA

async def receber_senha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    senha = update.message.text.strip()
    user_id = update.effective_user.id
    cpf = usuarios.get(user_id, {}).get("cpf")

    if not cpf or not senha:
        await update.message.reply_text("❌ CPF ou senha inválidos.")
        context.user_data["conversation"] = None
        return ConversationHandler.END

    resultados = df[(df["Login"] == cpf) & (df["Senha"] == senha)]
    if resultados.empty:
        await update.message.reply_text("⚠️ Opa, algo está incorreto. Verifique se o CPF está sem pontos ou traços, ou se a senha que você digitou é a correta.")
        return ConversationHandler.END

    meses_disponiveis = (
        resultados["Data"]
        .dt.to_period("M")
        .dropna()
        .drop_duplicates()
        .sort_values()
        .astype(str)
        .str.replace("-", "/")
    )

    keyboard = [[InlineKeyboardButton(mes, callback_data=mes)] for mes in meses_disponiveis]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "✅ Login realizado com sucesso!\nEscolha o mês que deseja visualizar:",
        reply_markup=reply_markup
    )

    usuarios[user_id]["resultados"] = resultados
    context.user_data["conversation"] = SELECIONAR_MES
    return SELECIONAR_MES

async def selecionar_mes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    mes_selecionado = query.data.replace("/", "-")
    user_id = query.from_user.id
    resultados = usuarios[user_id]["resultados"]

    resultados["Periodo"] = resultados["Data"].dt.to_period("M").astype(str)
    resultados_filtrados = resultados[resultados["Periodo"] == mes_selecionado]

    if resultados_filtrados.empty:
        await query.edit_message_text("⚠️ Nenhum dado encontrado para esse mês.")
        return ConversationHandler.END

    ult = resultados_filtrados.iloc[-1]
    detalhes = ""
    total_geral = resultados_filtrados["TOTAL"].sum()
    for _, dia in resultados_filtrados.iterrows():
        data_fmt = dia["Data"].strftime("%d/%m") if not pd.isna(dia["Data"]) else "-"
        abs_valor = dia["ABS"]
        valor_dia = fmt(dia["TOTAL"])
        detalhes += f"• {data_fmt} - ABS: {abs_valor} - Total: {valor_dia}\n"

    indicadores = "\n".join([f"• {col}: {fmt(ult[col])}" for col in INDICADORES if col in ult])
    desenvolvimento = "\n".join([
        f"• {col}: {int(ult[col]*100)}%" if 'SKAP' in col or 'SAKP' in col else f"• {col}: {ult[col]}"
        for col in DESENVOLVIMENTO if col in ult
    ])

    mensagem = (
        f"🧍 Nome: {ult['Nome']}\n"
        f"💰 Total recebido no período: {fmt(total_geral)}\n\n"
        f"📅 Detalhamento por dia:\n{detalhes}\n"
        f"📊 Indicadores de Desempenho (referente a {ult['Data'].strftime('%d/%m')}):\n{indicadores}\n\n"
        f"🌱 Desenvolvimento:\n{desenvolvimento}"
    )
    await query.edit_message_text(mensagem)
    context.user_data["conversation"] = None
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Operação cancelada.", reply_markup=ReplyKeyboardRemove())
    context.user_data["conversation"] = None
    return ConversationHandler.END

async def entrada_padrao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("conversation") in [LOGIN, SENHA, SELECIONAR_MES]:
        return
    keyboard = [[InlineKeyboardButton("🚀 Iniciar Consulta de RV", url="https://t.me/HoriCaruaru_bot?start=start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 Olá! Para começar, clique no botão abaixo:", reply_markup=reply_markup)

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_login)],
            SENHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_senha)],
            SELECIONAR_MES: [CallbackQueryHandler(selecionar_mes)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, entrada_padrao))

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        webhook_url=os.environ.get("WEBHOOK_URL")
    )

if __name__ == "__main__":
    main()
