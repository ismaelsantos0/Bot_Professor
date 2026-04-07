import os
import psycopg2
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DB_URL)

async def limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msgs = context.user_data.get("last_messages", [])
    for msg_id in msgs:
        try:
            await context.bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
    context.user_data["last_messages"] = []

# =========================
# MENUS E NAVEGAÇÃO
# =========================
async def enviar_menu_principal(chat_id, context):
    keyboard = [
        [InlineKeyboardButton("🚀 Iniciar os Estudos", callback_data="iniciar_estudos")],
        [InlineKeyboardButton("📝 Resolver Questões", callback_data="nova_questao")],
        [InlineKeyboardButton("📅 Matérias do Dia", callback_data="materias_dia")]
    ]
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text="📚 *Menu de Estudos - ALE-RR (FCC)*\nO que vamos fazer agora?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    context.user_data.setdefault("last_messages", []).append(msg.message_id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await limpar(update, context)
    if update.message:
        await enviar_menu_principal(update.effective_chat.id, context)

# =========================
# LÓGICA DOS BOTÕES
# =========================
async def processar_resposta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dados = query.data

    # VOLTAR AO MENU PRINCIPAL
    if dados == "menu_principal":
        await limpar(update, context)
        return await enviar_menu_principal(update.effective_chat.id, context)

    # MATÉRIAS DO DIA (Cronograma Dinâmico)
    if dados == "materias_dia":
        await limpar(update, context)
        hoje = datetime.datetime.today().weekday()
        
        cronograma = {
            0: "📚 *Segunda-feira*\n- Língua Portuguesa\n- Legislação Institucional",
            1: "📚 *Terça-feira*\n- Conhecimentos Específicos\n- Geografia e História de Roraima",
            2: "📚 *Quarta-feira*\n- Língua Portuguesa\n- Conhecimentos Específicos",
            3: "📚 *Quinta-feira*\n- Legislação Institucional\n- Revisão da Parte Específica",
            4: "📚 *Sexta-feira*\n- Geografia e História de Roraima\n- Conhecimentos Específicos",
            5: "📚 *Sábado*\n- Revisão da Semana\n- Leitura de Lei Seca",
            6: "📚 *Domingo*\n- 📝 Dia de focar só em Resolver Questões e Simulados!"
        }
        
        texto_hoje = f"📅 *Seu Plano para Hoje:*\n\n{cronograma[hoje]}\n\nBora bater a meta?"
        
        keyboard = [
            [InlineKeyboardButton("🚀 Iniciar Estudos", callback_data="iniciar_estudos")],
            [InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_principal")]
        ]
        
        msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=texto_hoje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        context.user_data.setdefault("last_messages", []).append(msg.message_id)

    # INICIAR ESTUDOS (Pode virar um Pomodoro no futuro)
    if dados == "iniciar_estudos":
        await limpar(update, context)
        keyboard = [[InlineKeyboardButton("⬅️ Pausar / Voltar", callback_data="menu_principal")]]
        msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⏱️ *Sessão de estudos iniciada!* Desligue as distrações e foco total. Quando terminar, volte aqui.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        context.user_data.setdefault("last_messages", []).append(msg.message_id)

    # NOVA QUESTÃO (A lógica que já montamos antes com o BD)
    if dados == "nova_questao":
        await limpar(update, context)
        # ... (Aqui entra aquele bloco try/except com o SELECT do banco de dados que fizemos antes)
        # msg = await context.bot.send_message(...)
        # context.user_data.setdefault("last_messages", []).append(msg.message_id)
        pass

def main():
    print("🚀 Bot iniciando...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(processar_resposta)) 
    print("✅ Bot rodando!")
    app.run_polling()

if __name__ == "__main__":
    main()
