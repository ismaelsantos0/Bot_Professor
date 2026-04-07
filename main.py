import os
import psycopg2
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DATABASE_URL")

# =========================
# BANCO
# =========================
def get_conn():
    return psycopg2.connect(DB_URL)

# =========================
# MENU
# =========================
def get_menu():
    keyboard = [
        ["📚 Nova Questão"],
        ["❌ Sair"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# =========================
# LIMPAR MENSAGENS
# =========================
async def limpar(update, context):
    try:
        chat_id = update.effective_chat.id
        msgs = context.user_data.get("last_messages", [])

        for msg_id in msgs:
            try:
                await context.bot.delete_message(chat_id, msg_id)
            except:
                pass

        context.user_data["last_messages"] = []

    except Exception as e:
        print("Erro ao limpar:", e)

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await limpar(update, context)

    msg = await update.message.reply_text(
        "🤖 Bot de estudos FCC pronto!\nEscolha uma opção:",
        reply_markup=get_menu()
    )

    context.user_data["last_messages"] = [msg.message_id]

# =========================
# QUESTÃO
# =========================
async def questao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await limpar(update, context)

    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT * FROM questoes ORDER BY RANDOM() LIMIT 1")
        q = cur.fetchone()

        if not q:
            msg = await update.message.reply_text("⚠️ Nenhuma questão no banco.")
            context.user_data["last_messages"] = [msg.message_id]
            return

        context.user_data["questao"] = q

        texto = f"""
📚 {q[1]}

{q[2]}

A) {q[3]}
B) {q[4]}
C) {q[5]}
D) {q[6]}
"""

        msg = await update.message.reply_text(texto)

        context.user_data["last_messages"] = [msg.message_id]

        cur.close()
        conn.close()

    except Exception as e:
        print("ERRO QUESTAO:", e)
        msg = await update.message.reply_text("❌ Erro ao buscar questão.")
        context.user_data["last_messages"] = [msg.message_id]

# =========================
# RESPOSTA
# =========================
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_user = update.message.text.strip()

    # MENU
    if texto_user == "📚 Nova Questão":
        return await questao(update, context)

    if texto_user == "❌ Sair":
        return await start(update, context)

    resposta = texto_user.upper()
    q = context.user_data.get("questao")

    if not q:
        msg = await update.message.reply_text("Use o menu.")
        context.user_data["last_messages"] = [msg.message_id]
        return

    correta = q[7]
    acertou = resposta == correta

    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO respostas (user_id, questao_id, resposta, acertou) VALUES (%s,%s,%s,%s)",
            (update.effective_user.id, q[0], resposta, acertou)
        )
        conn.commit()

        cur.close()
        conn.close()

    except Exception as e:
        print("ERRO DB:", e)

    if acertou:
        texto = "✅ Acertou!"
    else:
        texto = f"❌ Errou! Resposta correta: {correta}"

    msg = await update.message.reply_text(texto)

    # salva pra apagar depois
    context.user_data["last_messages"].append(msg.message_id)

# =========================
# ERROS GERAIS
# =========================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"Erro geral: {context.error}")

# =========================
# MAIN
# =========================
def main():
    print("🚀 Bot iniciando...")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("questao", questao))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    app.add_error_handler(error_handler)

    print("✅ Bot rodando!")
    app.run_polling()

# =========================
# START
# =========================
if __name__ == "__main__":
    main()
