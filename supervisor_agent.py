from agno.agent import Agent
from agno.models.ollama import Ollama

# =========================================
# MEMÓRIA DO SUPERVISOR
# =========================================

supervisor_memory = {
    "historico_validacoes": [],
    "respostas_aprovadas": [],
    "erros_detectados": []
}

# =========================================
# TOOLS
# =========================================

def validar_campos(dados):
    campos_obrigatorios = [
        "problema_usuario",
        "categoria",
        "solucao_tecnica",
        "resposta_final"
    ]

    erros = []

    for campo in campos_obrigatorios:
        if campo not in dados or not dados[campo]:
            erros.append(f"Campo ausente: {campo}")

    return erros


def validar_tamanho_resposta(texto):
    if len(texto.strip()) < 30:
        return "Resposta muito curta."
    return None


def detectar_palavras_proibidas(texto):
    palavras_proibidas = [
        "não sei",
        "impossível",
        "erro fatal",
        "inválido"
    ]

    encontrados = []

    for palavra in palavras_proibidas:
        if palavra.lower() in texto.lower():
            encontrados.append(palavra)

    return encontrados


def calcular_score(erros):
    score = 100

    score -= len(erros) * 15

    if score < 0:
        score = 0

    return score

# =========================================
# AGENTE SUPERVISOR
# =========================================

supervisor_agent = Agent(
    name="Supervisor",
    #model=Ollama(id="llama3.2:1b"), #Leve
    model=Ollama(id="llama3.1:8b"), #Pesado

    description="""
    Você é um supervisor inteligente responsável
    por validar respostas de suporte técnico.
    """,

    instructions=[
        "Verifique se a resposta é coerente com o problema.",
        "Analise clareza e qualidade da resposta.",
        "Detecte inconsistências.",
        "Responda de forma objetiva.",
        "Informe se a resposta deve ser aprovada ou revisada."
    ],

    markdown=True
)

# =========================================
# WORKFLOW PRINCIPAL
# =========================================

def supervisionar_fluxo(dados_fluxo):

    erros = []

    # -------------------------------------
    # ETAPA 1 - VALIDAR CAMPOS
    # -------------------------------------

    erros_campos = validar_campos(dados_fluxo)
    erros.extend(erros_campos)

    # -------------------------------------
    # ETAPA 2 - VALIDAR TAMANHO
    # -------------------------------------

    erro_tamanho = validar_tamanho_resposta(
        dados_fluxo["resposta_final"]
    )

    if erro_tamanho:
        erros.append(erro_tamanho)

    # -------------------------------------
    # ETAPA 3 - PALAVRAS PROIBIDAS
    # -------------------------------------

    palavras_detectadas = detectar_palavras_proibidas(
        dados_fluxo["resposta_final"]
    )

    if palavras_detectadas:
        erros.append(
            f"Palavras inadequadas detectadas: {palavras_detectadas}"
        )

    # -------------------------------------
    # ETAPA 4 - ANÁLISE COM LLM
    # -------------------------------------

    prompt_supervisao = f"""
    Analise a seguinte resposta de suporte técnico.

    Problema do usuário:
    {dados_fluxo["problema_usuario"]}

    Categoria:
    {dados_fluxo["categoria"]}

    Solução técnica:
    {dados_fluxo["solucao_tecnica"]}

    Resposta final:
    {dados_fluxo["resposta_final"]}

    Verifique:
    - coerência
    - clareza
    - qualidade
    - completude

    Informe se a resposta deve ser APROVADA
    ou necessita REVISÃO.
    """

    analise_llm = supervisor_agent.run(prompt_supervisao)

    # -------------------------------------
    # ETAPA 5 - CALCULAR SCORE
    # -------------------------------------

    score = calcular_score(erros)

    # -------------------------------------
    # ETAPA 6 - DECISÃO FINAL
    # -------------------------------------

    status = "APROVADO"

    if len(erros) > 0 or score < 70:
        status = "REVISÃO NECESSÁRIA"

    # -------------------------------------
    # ETAPA 7 - MEMÓRIA
    # -------------------------------------

    supervisor_memory["historico_validacoes"].append({
        "status": status,
        "score": score
    })

    if status == "APROVADO":
        supervisor_memory["respostas_aprovadas"].append(
            dados_fluxo["resposta_final"]
        )

    if erros:
        supervisor_memory["erros_detectados"].append(erros)

    # -------------------------------------
    # RETORNO FINAL
    # -------------------------------------

    return {
        "status": status,
        "score": score,
        "erros": erros,
        "analise_llm": analise_llm.content
    }