import os
import pandas as pd
from datetime import datetime
from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ChatAction

TOKEN = os.getenv("BOT_TOKEN")
EXCEL_FILE = "04. Farol.xlsx"

INDICADORES = ["EFC", "RESSUPRIMENTO", "EFD", "ATIV. TURNO A", "ATIV. TURNO B", "MONTAGEM", "TMA", "CARREG. AG", "CARREG"]
DESENVOLVIMENTO = ["CICLO DE GENTE", "SKAP - TECNICO", "SKAP - ESPECIFICO", "SAKP - EMPODERAMENTO"]

IDS_AUTORIZADOS = [6275635034]  # Seu ID de admin

# ===============================
# LEITURA E PADRONIZAÇÃO DA BASE
# ===============================

df = pd.read_excel(EXCEL_FILE)

# Padroniza CPF/Login
df["Login"] = (
    df["Login"]
    .astype(str)
    .str.replace(".0", "", regex=False)
    .str.replace(".", "", regex=False)
    .str.replace("-", "", regex=False)
    .str.replace(" ", "", regex=False)
    .str.strip()
)

# Garante que Data seja datetime
if not pd.api.types.is_datetime64_any_dtype(df["Data"]):
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")

LOGIN, SELECIONAR_MES = range(2)
usuarios = {}

def fmt(valor):
    if pd.isna(valor):
        return "N/A"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def registrar_acesso(user_id, nome_usuario, username, cpf, mes):
    with open("acessos.csv", "a", encoding="utf-8") as f:
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linha = f"{data},{user_id},{nome_usuario},{username},{cpf},{mes}\n"
        f.write(linha)

async def relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in IDS_AUTORIZADOS:
        await update.message.reply_text("❌ Acesso negado.")
        return

    await update.message.chat.send_action(action=ChatAction.UPLOAD_DOCUMENT)
    try:
        await update.message.reply_document(document=open("acessos.csv", "rb"))
    except FileNotFoundError:
        await update.message.reply_text("⚠️ Nenhum acesso registrado ainda.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("👤 Digite seu CPF (somente números):")
    return LOGIN

async def receber_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cpf = (
        update.message.text
        .strip()
        .replace(".", "")
        .replace("-", "")
        .replace(" ", "")
    )

    resultados = df[df["Login"] == cpf]

    if resultados.empty:
        await update.message.reply_text(
            "⚠️ CPF não encontrado. Verifique se digitou corretamente, sem pontos ou traços."
        )
        return ConversationHandler.END

    usuarios[update.effective_user.id] = {
        "cpf": cpf,
        "resultados": resultados.copy()
    }

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
        "✅ CPF validado!\nEscolha o mês que deseja visualizar:",
        reply_markup=reply_markup
    )

    return SELECIONAR_MES

async def selecionar_mes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    mes_selecionado = query.data.replace("/", "-")

    user_id = query.from_user.id
    resultados = usuarios[user_id]["resultados"].copy()

    registrar_acesso(
        user_id=user_id,
        nome_usuario=query.from_user.full_name,
        username=query.from_user.username or "",
        cpf=usuarios[user_id]["cpf"],
        mes=mes_selecionado
    )

    resultados["Periodo"] = resultados["Data"].dt.to_period("M").astype(str)
    resultados_filtrados = resultados[resultados["Periodo"] == mes_selecionado]

    if resultados_filtrados.empty:
        await query.edit_message_text("⚠️ Nenhum dado encontrado para esse mês.")
        return ConversationHandler.END

    ult = resultados_filtrados.iloc[-1]
    total_geral = resultados_filtrados["TOTAL"].sum()

    detalhes = ""
    for _, dia in resultados_filtrados.iterrows():
        data_fmt = dia["Data"].strftime("%d/%m") if not pd.isna(dia["Data"]) else "-"
        abs_valor = dia.get("ABS", "-")
        valor_dia = fmt(dia.get("TOTAL", 0))
        detalhes += f"• {data_fmt} - ABS: {abs_valor} - Total: {valor_dia}\n"

    hoje = pd.Timestamp.now().normalize()
    ontem = hoje - pd.Timedelta(days=1)

    if ontem.weekday() == 6:
        dia_referencia = hoje - pd.Timedelta(days=2)
    else:
        dia_referencia = ontem

    linha_indicador = resultados_filtrados[resultados_filtrados["Data"] == dia_referencia]
    base_indicador = linha_indicador.iloc[0] if not linha_indicador.empty else ult

    indicadores = "\n".join([
        f"• {col}: {fmt(base_indicador[col])}"
        for col in INDICADORES if col in base_indicador
    ])

    desenvolvimento = "\n".join([
        f"• {col}: {int(base_indicador[col]*100)}%" if 'SKAP' in col or 'SAKP' in col
        else f"• {col}: {base_indicador[col]}"
        for col in DESENVOLVIMENTO if col in base_indicador
    ])

    mensagem = (
        f"🧍 Nome: {base_indicador.get('Nome','-')}\n"
        f"💰 Total recebido no período: {fmt(total_geral)}\n\n"
        f"📅 Detalhamento por dia:\n{detalhes}\n"
        f"📊 Indicadores de Desempenho (referente a {dia_referencia.strftime('%d/%m')}):\n{indicadores}\n\n"
        f"🌱 Desenvolvimento:\n{desenvolvimento}"
    )

    await query.edit_message_text(mensagem)
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Operação cancelada.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def entrada_padrao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🚀 Iniciar Consulta de RV", url="https://t.me/HoriCaruaru_bot?start=start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Olá! Para começar, clique no botão abaixo:",
        reply_markup=reply_markup
    )

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_login)],
            SELECIONAR_MES: [CallbackQueryHandler(selecionar_mes)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("relatorio", relatorio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, entrada_padrao))

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        webhook_url=os.environ.get("WEBHOOK_URL")
    )

if __name__ == "__main__":
    main()