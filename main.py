import os
import random
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
# CONFIGURAÇÕES
# =========================
TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
modelo_gemini = genai.GenerativeModel('gemini-2.5-flash')

# =========================
# EDITAL ALE-RR CARGO 38
# =========================
edital_ale_rr = {
    "Língua Portuguesa": [
        "Ortografia oficial, acentuação gráfica e crase", 
        "Compreensão e interpretação de textos", 
        "Morfossintaxe, concordância e regência", 
        "Pontuação", 
        "Coesão e coerência textual"
    ],
    "Legislação Institucional": [
        "Regimento Interno da ALE-RR", 
        "Constituição do Estado de Roraima (Poder Legislativo)", 
        "Estatuto dos Servidores Públicos de Roraima (LC 053/2001)"
    ],
    "História e Geografia de Roraima": [
        "Criação do Território Federal do Rio Branco e elevação a Estado", 
        "Economia e aspectos sociais históricos de Roraima", 
        "Geografia física, clima e vegetação de Roraima"
    ],
    "Conhecimentos Específicos": [
        "Direito Constitucional: Direitos e Garantias Fundamentais (Art. 5 ao 17)", 
        "Direito Constitucional: Poder Legislativo e Processo Legislativo", 
        "Direito Administrativo: Atos e Poderes Administrativos", 
        "Direito Administrativo: Nova Lei de Licitações (14.133/2021)", 
        "Administração Pública: Centralização, descentralização e desconcentração", 
        "AFO: Princípios orçamentários, PPA, LDO e LOA", 
        "Redação Oficial e Legística (Elaboração de Leis)"
    ]
}

# =========================
# FUNÇÕES AUXILIARES
# =========================
def get_conn():
    return psycopg2.connect(DB_URL)

async def pedir_ao_gemini(prompt: str) -> str:
    try:
        resposta = await modelo_gemini.generate_content_async(prompt)
        texto = resposta.text
        # Trava de segurança para o Telegram não recusar mensagens gigantes
        if len(texto) > 4000:
            texto = texto[:3900] + "\n\n[⚠️ Texto reduzido para caber no limite do Telegram]"
        return texto
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
# COMANDOS DIRETOS
# =========================
async def cmd_estudar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assunto_solicitado = " ".join(context.args)
    
    if not assunto_solicitado:
        await update.message.reply_text("⚠️ Uso correto: `/estudar [assunto]`\nExemplo: `/estudar crase`", parse_mode="Markdown")
        return

    msg_loading = await update.message.reply_text(f"⏳ *Preparando material sobre: {assunto_solicitado}...*", parse_mode="Markdown")

    prompt = f"""
    Você é um professor especialista na banca FCC. Seu aluno está focado no edital da ALE-RR, Cargo 38 (Assistente Legislativo).
    O aluno pediu para estudar: '{assunto_solicitado}'.
    1. Verifique mentalmente se isso tem a ver com o edital.
    2. Dê uma explicação teórica direta, com foco em como a banca FCC cobra isso.
    3. Mostre as 'pegadinhas' mais comuns da FCC.
    4. Dê um exemplo prático.
    CRÍTICO: Sua explicação deve ter no máximo 3500 caracteres. Seja conciso.
    Formate o texto para o aplicativo Telegram (use emojis e negrito).
    """
    
    aula_texto = await pedir_ao_gemini(prompt)
    
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_loading.message_id)
    await update.message.reply_text(f"📚 *Aula Rápida*\n\n{aula_texto}", parse_mode="Markdown")

async def cmd_explicar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Uso correto: `/explicar [ID da questão]`\nExemplo: `/explicar 15`", parse_mode="Markdown")
        return

    questao_id = context.args[0]

    if not questao_id.isdigit():
        await update.message.reply_text("❌ O ID da questão deve ser um número inteiro.")
        return

    msg_loading = await update.message.reply_text(f"⏳ *Analisando a questão {questao_id}...*", parse_mode="Markdown")

    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT materia, assunto, pergunta, correta FROM questoes WHERE id = %s", (questao_id,))
        q_data = cur.fetchone()
        cur.close()
        conn.close()

        if not q_data:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_loading.message_id)
            await update.message.reply_text(f"❌ Nenhuma questão encontrada com o ID {questao_id} no banco de dados.")
            return

        prompt = f"""
        Sou um aluno estudando para a ALE-RR (nível médio, banca FCC). 
        A questão de {q_data[0]} era: "{q_data[2]}".
        O gabarito oficial diz que a correta é a "{q_data[3]}".
        Explique de forma direta o porquê dessa ser a correta e qual é a 'pegadinha' da FCC.
        CRÍTICO: Sua explicação deve ter no máximo 3500 caracteres. Seja conciso.
        """
        explicacao = await pedir_ao_gemini(prompt)
        
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_loading.message_id)
        await update.message.reply_text(f"💡 *Explicação da Questão {questao_id}:*\n\n{explicacao}", parse_mode="Markdown")

    except Exception as e:
        print("ERRO BUSCA ID:", e)
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_loading.message_id)
        await update.message.reply_text("❌ Erro ao buscar questão no banco de dados.")

# =========================
# MENUS
# =========================
async def enviar_menu_principal(chat_id, context):
    keyboard = [
        [InlineKeyboardButton("🚀 Iniciar Estudos (Aulas por IA)", callback_data="iniciar_estudos")],
        [InlineKeyboardButton("📝 Resolver Questões do Banco", callback_data="nova_questao")],
        [InlineKeyboardButton("📅 Meu Cronograma", callback_data="materias_dia")]
    ]
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text="📚 *Menu de Estudos - ALE-RR (FCC)*\nO que vamos focar hoje?",
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

    if dados == "menu_principal":
        await limpar(update, context)
        return await enviar_menu_principal(chat_id, context)

    if dados == "materias_dia":
        await limpar(update, context)
        hoje = datetime.datetime.today().weekday()
        
        cronograma = {
            0: "📚 *Segunda-feira*\n- Língua Portuguesa\n- Legislação Institucional (ALE-RR)",
            1: "📚 *Terça-feira*\n- Conhecimentos Específicos\n- História e Geografia de Roraima",
            2: "📚 *Quarta-feira*\n- Língua Portuguesa\n- Conhecimentos Específicos",
            3: "📚 *Quinta-feira*\n- Legislação Institucional (ALE-RR)\n- Revisão",
            4: "📚 *Sexta-feira*\n- História e Geografia de Roraima\n- Conhecimentos Específicos",
            5: "📚 *Sábado*\n- Revisão da Semana\n- Leitura de Lei Seca",
            6: "📚 *Domingo*\n- 📝 Dia de focar só em Resolver Questões e Simulados!"
        }
        
        texto_hoje = f"📅 *Seu Plano para Hoje:*\n\n{cronograma[hoje]}\n\nBora bater a meta?"
        keyboard = [
            [InlineKeyboardButton("🚀 Escolher Matéria para Estudar", callback_data="iniciar_estudos")],
            [InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_principal")]
        ]
        msg = await context.bot.send_message(chat_id, text=texto_hoje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        context.user_data.setdefault("last_messages", []).append(msg.message_id)

    if dados == "iniciar_estudos":
        await limpar(update, context)
        keyboard = [
            [InlineKeyboardButton("🇵🇹 Língua Portuguesa", callback_data="aula_Língua Portuguesa")],
            [InlineKeyboardButton("🗺️ Hist. e Geo. de Roraima", callback_data="aula_História e Geografia de Roraima")],
            [InlineKeyboardButton("⚖️ Legislação Institucional", callback_data="aula_Legislação Institucional")],
            [InlineKeyboardButton("📚 Conhecimentos Específicos", callback_data="aula_Conhecimentos Específicos")],
            [InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_principal")]
        ]
        msg = await context.bot.send_message(chat_id, text="📚 *Qual matéria do edital da ALE-RR você quer que a IA te ensine agora?*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        context.user_data.setdefault("last_messages", []).append(msg.message_id)

    if dados.startswith("aula_"):
        materia_foco = dados.split("_")[1]
        await limpar(update, context)
        
        msg_loading = await context.bot.send_message(chat_id, f"⏳ *O professor IA está separando um tópico de {materia_foco}...*", parse_mode="Markdown")
        context.user_data.setdefault("last_messages", []).append(msg_loading.message_id)

        assunto_sorteado = random.choice(edital_ale_rr[materia_foco])

        prompt = f"""
        Você é um professor especialista em concursos da banca FCC. Seu aluno está focado no edital da ALE-RR, Cargo 38 (Assistente Legislativo).
        O assunto EXATO de hoje é: '{assunto_sorteado}' (dentro da disciplina de {materia_foco}).
        Siga as instruções:
        1. Informe qual foi o tópico escolhido logo no início.
        2. Dê uma explicação teórica direta, com foco em como a banca FCC cobra isso.
        3. Mostre as 'pegadinhas' mais comuns da banca.
        4. Dê um exemplo de como a questão aparece na prova.
        CRÍTICO: Sua explicação deve ter no máximo 3500 caracteres. Seja conciso e direto ao ponto.
        Formate o texto para o aplicativo Telegram (use emojis, negrito nas palavras-chave e parágrafos curtos).
        """
        
        aula_texto = await pedir_ao_gemini(prompt)
        
        keyboard = [
            [InlineKeyboardButton("🔄 Gerar outro assunto", callback_data=f"aula_{materia_foco}")],
            [InlineKeyboardButton("📝 Fazer Questões", callback_data="nova_questao")],
            [InlineKeyboardButton("⬅️ Menu de Matérias", callback_data="iniciar_estudos")]
        ]
        
        await limpar(update, context)
        msg = await context.bot.send_message(chat_id, text=f"{aula_texto}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        context.user_data.setdefault("last_messages", []).append(msg.message_id)

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
                msg = await context.bot.send_message(chat_id, "⚠️ Nenhuma questão no banco de dados ainda. Alimente o banco para praticar!")
                context.user_data.setdefault("last_messages", []).append(msg.message_id)
                return

            questao_id = q[0] 
            texto = f"📚 *{q[1]}*\n\n{q[5]}\n\nA) {q[6]}\nB) {q[7]}\nC) {q[8]}\nD) {q[9]}"
            if q[10]: 
                texto += f"\nE) {q[10]}"

            keyboard = [
                [InlineKeyboardButton("A", callback_data=f"resp_{questao_id}_A"), InlineKeyboardButton("B", callback_data=f"resp_{questao_id}_B"), InlineKeyboardButton("C", callback_data=f"resp_{questao_id}_C")],
                [InlineKeyboardButton("D", callback_data=f"resp_{questao_id}_D")]
            ]
            if q[10]: 
                 keyboard[1].append(InlineKeyboardButton("E", callback_data=f"resp_{questao_id}_E"))
                 
            keyboard.append([InlineKeyboardButton("⬅️ Menu Principal", callback_data="menu_principal")])

            msg = await context.bot.send_message(chat_id, text=texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            context.user_data.setdefault("last_messages", []).append(msg.message_id)

        except Exception as e:
            print("ERRO QUESTAO:", e)
            msg = await context.bot.send_message(chat_id, "❌ Erro ao buscar questão no banco.")
            context.user_data.setdefault("last_messages", []).append(msg.message_id)

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

        texto_resultado = f"✅ *Acertou, futuro servidor!*" if acertou else f"❌ *Errou!* A alternativa correta era a *{correta}*."
        
        keyboard = [[InlineKeyboardButton("📚 Próxima Questão", callback_data="nova_questao")]]
        
        if not acertou:
            keyboard.insert(0, [InlineKeyboardButton("🤖 IA, por que eu errei?", callback_data=f"explicar_{questao_id}")])
            
        keyboard.append([InlineKeyboardButton("⬅️ Menu Principal", callback_data="menu_principal")])

        await limpar(update, context)
        msg = await context.bot.send_message(chat_id, text=texto_resultado, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        context.user_data.setdefault("last_messages", []).append(msg.message_id)

    if dados.startswith("explicar_"):
        questao_id = dados.split("_")[1]
        await limpar(update, context)
        msg_loading = await context.bot.send_message(chat_id, "⏳ *O Professor está analisando a questão do banco...*", parse_mode="Markdown")
        context.user_data.setdefault("last_messages", []).append(msg_loading.message_id)
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT pergunta, correta FROM questoes WHERE id = %s", (questao_id,))
        q_data = cur.fetchone()
        cur.close()
        conn.close()
        
        if q_data:
            prompt = f"""
            Sou um aluno estudando para a ALE-RR (nível médio, banca FCC). 
            A questão que acabei de fazer era: "{q_data[0]}".
            A resposta correta é a alternativa "{q_data[1]}".
            Explique de forma direta o porquê dessa ser a correta e qual é a 'pegadinha' ou regra usada pela FCC aqui.
            CRÍTICO: Sua explicação deve ter no máximo 3500 caracteres. Seja conciso.
            """
            explicacao = await pedir_ao_gemini(prompt)
        else:
            explicacao = "Não consegui encontrar os dados da questão no banco."

        keyboard = [
            [InlineKeyboardButton("📚 Fazer Outra Questão", callback_data="nova_questao")],
            [InlineKeyboardButton("⬅️ Menu Principal", callback_data="menu_principal")]
        ]
        
        await limpar(update, context)
        msg = await context.bot.send_message(chat_id, text=f"💡 *Explicação da Questão {questao_id}:*\n\n{explicacao}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        context.user_data.setdefault("last_messages", []).append(msg.message_id)

def main():
    print("🚀 Bot da ALE-RR iniciando...")
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("estudar", cmd_estudar))
    app.add_handler(CommandHandler("explicar", cmd_explicar))
    app.add_handler(CallbackQueryHandler(processar_resposta)) 
    
    print("✅ Bot rodando e conectado ao Gemini!")
    app.run_polling()

if __name__ == "__main__":
    main()
