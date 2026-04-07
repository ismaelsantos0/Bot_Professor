import os
import psycopg2
from telegram import Update
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
# COMANDO /start
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot de estudos FCC online!\nUse /questao para começar.")

# =========================
# COMANDO /questao
# =========================
async def questao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT * FROM questoes ORDER BY RANDOM() LIMIT 1")
        q = cur.fetchone()

        if not q:
            await update.message.reply_text("⚠️ Nenhuma questão no banco ainda.")
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
        await update.message.reply_text(texto)

        cur.close()
        conn.close()

    except Exception as e:
        print("ERRO QUESTAO:", e)
        await update.message.reply_text("❌ Erro ao buscar questão.")

# =========================
# RESPOSTA DO USUÁRIO
# =========================
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        resposta = update.message.text.strip().upper()
        q = context.user_data.get("questao")

        if not q:
            await update.message.reply_text("Use /questao primeiro.")
            return

        correta = q[7]

        acertou = resposta == correta

        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO respostas (user_id, questao_id, resposta, acertou) VALUES (%s,%s,%s,%s)",
            (update.effective_user.id, q[0], resposta, acertou)
        )
        conn.commit()

        cur.close()
        conn.close()

        if acertou:
            await update.message.reply_text("✅ Acertou!")
        else:
            await update.message.reply_text(f"❌ Errou! Resposta correta: {correta}")

    except Exception as e:
        print("ERRO RESPOSTA:", e)
        await update.message.reply_text("❌ Erro ao processar resposta.")

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
