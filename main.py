import os
import psycopg2
import datetime
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# =========================
# CONFIGURAÇÕES (Railway Env Vars)
# =========================
TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configuração da IA
genai.configure(api_key=GEMINI_API_KEY)
modelo_gemini = genai.GenerativeModel('gemini-2.5-flash')

# =========================
# FUNÇÕES DE BANCO E IA
# =========================
def get_conn():
    return psycopg2.connect(DB_URL)

async def pedir_ao_gemini(prompt: str) -> str:
    try:
        resposta = await modelo_gemini.generate_content_async(prompt)
        return resposta.text
    except Exception as e:
        print(f"Erro no Gemini: {e}")
        return "❌ Ops! Meu cérebro de IA deu uma travada. Tente novamente."

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
# MENUS
# =========================
async def enviar_menu_principal(chat_id, context):
    keyboard = [
        [InlineKeyboardButton("🚀 Iniciar os Estudos (IA)", callback_data="iniciar_estudos")],
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
# LÓGICA PRINCIPAL (ROTEADOR)
# =========================
async def processar_resposta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dados = query.data
    chat_id = update.effective_chat.id

    # ---------- MENU PRINCIPAL ----------
    if dados == "menu_principal":
        await limpar(update, context)
        return await enviar_menu_principal(chat_id, context)

    # ---------- MATÉRIAS DO DIA ----------
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
        msg = await context.bot.send_message(chat_id, text=texto_hoje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        context.user_data.setdefault("last_messages", []).append(msg.message_id)

    # ---------- INICIAR ESTUDOS (GEMINI) ----------
    if dados == "iniciar_estudos":
        await limpar(update, context)
        msg_loading = await context.bot.send_message(chat_id, text="⏳ *O professor IA está preparando um resumo focado na FCC...*", parse_mode="Markdown")
        context.user_data.setdefault("last_messages", []).append(msg_loading.message_id)

        # No futuro, você pode ler a matéria direto do cronograma ou banco. 
        # Aqui, vamos sortear um tema de exemplo da ALE-RR.
        materia_foco = "Regimento Interno da Assembleia Legislativa de Roraima" 
        
        prompt = f"""
        Aja como um professor especialista em concursos públicos da banca FCC para cargos de Nível Médio.
        Crie um resumo direto ao ponto sobre '{materia_foco}'.
        O resumo deve conter:
        1. A regra principal.
        2. As exceções ou "pegadinhas" comuns.
        3. Como isso costuma cair em prova.
        Seja breve e formate bem para o Telegram (use emojis e negrito).
        """
        aula_texto = await pedir_ao_gemini(prompt)
        
        keyboard = [
            [InlineKeyboardButton("📝 Ir para Questões", callback_data="nova_questao")],
            [InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_principal")]
        ]
        
        await limpar(update, context)
        msg = await context.bot.send_message(chat_id, text=f"{aula_texto}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        context.user_data.setdefault("last_messages", []).append(msg.message_id)

    # ---------- NOVA QUESTÃO (POSTGRESQL) ----------
    if dados == "nova_questao":
        await limpar(update, context)
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT * FROM questoes ORDER BY RANDOM() LIMIT 1")
            q = cur.fetchone()
            cur.close()
            conn.close()

            if not q:
                msg = await context.bot.send_message(chat_id, "⚠️ Nenhuma questão no banco. Alimente o DB!")
                context.user_data.setdefault("last_messages", []).append(msg.message_id)
                return

            # q = (id, materia, assunto, ano, cargo, pergunta, A, B, C, D, E, correta)
            questao_id = q[0] 
            
            # Montando o texto adaptado para lidar com a alternativa E caso ela seja nula no banco
            texto = f"📚 *{q[1]}*\n\n{q[5]}\n\nA) {q[6]}\nB) {q[7]}\nC) {q[8]}\nD) {q[9]}"
            if q[10]: # Se existir alternativa E
                texto += f"\nE) {q[10]}"

            keyboard = [
                [InlineKeyboardButton("A", callback_data=f"resp_{questao_id}_A"), InlineKeyboardButton("B", callback_data=f"resp_{questao_id}_B"), InlineKeyboardButton("C", callback_data=f"resp_{questao_id}_C")],
                [InlineKeyboardButton("D", callback_data=f"resp_{questao_id}_D")]
            ]
            
            if q[10]: # Adiciona botão E se existir
                 keyboard[1].append(InlineKeyboardButton("E", callback_data=f"resp_{questao_id}_E"))
                 
            keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_principal")])

            msg = await context.bot.send_message(chat_id, text=texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            context.user_data.setdefault("last_messages", []).append(msg.message_id)

        except Exception as e:
            print("ERRO QUESTAO:", e)
            msg = await context.bot.send_message(chat_id, "❌ Erro ao buscar questão no banco.")
            context.user_data.setdefault("last_messages", []).append(msg.message_id)

    # ---------- PROCESSAR RESPOSTA DA QUESTÃO ----------
    if dados.startswith("resp_"):
        partes = dados.split("_")
        questao_id = partes[1]
        resposta_usuario = partes[2]

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT correta FROM questoes WHERE id = %s", (questao_id,))
        resultado = cur.fetchone()
        
        if not resultado:
            return await context.bot.send_message(chat_id, "Erro ao validar questão.")

        correta = resultado[0]
        acertou = (resposta_usuario == correta)

        try:
            cur.execute(
                "INSERT INTO respostas (user_id, questao_id, resposta, acertou) VALUES (%s,%s,%s,%s)",
                (update.effective_user.id, questao_id, resposta_usuario, acertou)
            )
            conn.commit()
        except Exception as e:
            print("ERRO DB SALVAR:", e)
        finally:
            cur.close()
            conn.close()

        texto_resultado = "✅ *Acertou!*" if acertou else f"❌ *Errou!* A resposta correta era a alternativa *{correta}*."
        
        keyboard = [[InlineKeyboardButton("📚 Próxima Questão", callback_data="nova_questao")]]
        
        if not acertou:
            keyboard.insert(0, [InlineKeyboardButton("🤖 Por que eu errei?", callback_data=f"explicar_{questao_id}")])
            
        keyboard.append([InlineKeyboardButton("⬅️ Menu Principal", callback_data="menu_principal")])

        await limpar(update, context)
        msg = await context.bot.send_message(chat_id, text=texto_resultado, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        context.user_data.setdefault("last_messages", []).append(msg.message_id)

    # ---------- PROFESSOR IA EXPLICA ERRO ----------
    if dados.startswith("explicar_"):
        questao_id = dados.split("_")[1]
        await limpar(update, context)
        msg_loading = await context.bot.send_message(chat_id, "⏳ *O Professor está analisando a questão...*", parse_mode="Markdown")
        context.user_data.setdefault("last_messages", []).append(msg_loading.message_id)
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT pergunta, correta FROM questoes WHERE id = %s", (questao_id,))
        q_data = cur.fetchone()
        cur.close()
        conn.close()
        
        if q_data:
            prompt = f"""
            Sou um aluno estudando para a FCC (nível médio). 
            A questão era: "{q_data[0]}".
            A resposta correta é a alternativa "{q_data[1]}".
            Explique de forma curta e direta o porquê dessa ser a correta e qual é a 'pegadinha'.
            """
            explicacao = await pedir_ao_gemini(prompt)
        else:
            explicacao = "Não consegui encontrar os dados da questão no banco."

        keyboard = [
            [InlineKeyboardButton("📚 Próxima Questão", callback_data="nova_questao")],
            [InlineKeyboardButton("⬅️ Menu Principal", callback_data="menu_principal")]
        ]
        
        await limpar(update, context)
        msg = await context.bot.send_message(chat_id, text=f"💡 *Explicação:*\n\n{explicacao}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        context.user_data.setdefault("last_messages", []).append(msg.message_id)

def main():
    print("🚀 Bot iniciando...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(processar_resposta)) 
    print("✅ Bot rodando!")
    app.run_polling()

if __name__ == "__main__":
    main()
