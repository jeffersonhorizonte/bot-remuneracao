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

    # 🎯 Lógica especial para definir qual dia usar nos indicadores:
    hoje = pd.Timestamp.now().normalize()
    ontem = hoje - pd.Timedelta(days=1)
    if ontem.weekday() == 6:  # domingo
        dia_referencia = hoje - pd.Timedelta(days=2)  # sábado
    else:
        dia_referencia = ontem

    if ult.get("CARGO", "").strip().upper() == "AJUDANTE" and ult.get("TURNO", "").strip().upper() == "C":
        dia_referencia = hoje

    linha_indicador = resultados_filtrados[resultados_filtrados["Data"] == dia_referencia]
    if not linha_indicador.empty:
        base_indicador = linha_indicador.iloc[0]
    else:
        base_indicador = ult

    indicadores = "\n".join([f"• {col}: {fmt(base_indicador[col])}" for col in INDICADORES if col in base_indicador])
    desenvolvimento = "\n".join([
        f"• {col}: {int(base_indicador[col]*100)}%" if 'SKAP' in col or 'SAKP' in col else f"• {col}: {base_indicador[col]}"
        for col in DESENVOLVIMENTO if col in base_indicador
    ])

    mensagem = (
        f"🧍 Nome: {base_indicador['Nome']}\n"
        f"💰 Total recebido no período: {fmt(total_geral)}\n\n"
        f"📅 Detalhamento por dia:\n{detalhes}\n"
        f"📊 Indicadores de Desempenho (referente a {dia_referencia.strftime('%d/%m')}):\n{indicadores}\n\n"
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
