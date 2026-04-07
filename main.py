from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import psycopg2
import os
import random

TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DB_URL)

async def questao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM questoes ORDER BY RANDOM() LIMIT 1")
    q = cur.fetchone()

    context.user_data['q'] = q

    texto = f"""
{q[2]}

A) {q[3]}
B) {q[4]}
C) {q[5]}
D) {q[6]}
"""
    await update.message.reply_text(texto)

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resposta = update.message.text.upper()
    q = context.user_data.get('q')

    if not q:
        await update.message.reply_text("Use /questao primeiro")
        return

    correta = q[7]

    conn = get_conn()
    cur = conn.cursor()

    acertou = resposta == correta

    cur.execute(
        "INSERT INTO respostas (user_id, questao_id, resposta, acertou) VALUES (%s,%s,%s,%s)",
        (update.effective_user.id, q[0], resposta, acertou)
    )
    conn.commit()

    if acertou:
        await update.message.reply_text("✅ Acertou!")
    else:
        await update.message.reply_text(f"❌ Errou! Resposta correta: {correta}")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("questao", questao))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

app.run_polling()
