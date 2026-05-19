from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from agno.agent import Agent
from agno.models.ollama import Ollama
from agno.os import AgentOS

from supervisor_agent import (
    supervisionar_fluxo,
    supervisor_agent
)

import json

# ============================================
# APP FASTAPI
# ============================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# MODELO LOCAL
# ============================================

model = Ollama(id="llama3.1:8b")

# Parte do Jean:

# ============================================
# BASE DE CONHECIMENTO
# ============================================

with open("knowledge_base.json", "r", encoding="utf-8") as f:
    base_conhecimento = json.load(f)

# Parte do Jean:

# ============================================
# TOOL DE CONSULTA
# ============================================

def buscar_solucao(categoria: str, problema: str):

    resultados = []

    categoria = categoria.lower()
    problema = problema.lower()

    for item in base_conhecimento:

        categoria_item = item["categoria"].lower()
        problema_item = item["problema"].lower()

        if categoria in categoria_item:

            palavras_problema = problema.split()

            match = any(
                palavra in problema_item
                for palavra in palavras_problema
            )

            if match:

                resultados.append({
                    "problema": item["problema"],
                    "causas": item["causas"],
                    "solucoes": item["solucoes"]
                })

    if not resultados:
        return {
            "status": "nenhum_resultado",
            "mensagem": "Nenhuma solução encontrada na base."
        }

    return resultados


def extrair_dados_classificacao(conteudo: str):

    dados = {
        "categoria": "desconhecida",
        "prioridade": "desconhecida"
    }

    for linha in conteudo.splitlines():

        linha_limpa = linha.strip()

        if linha_limpa.lower().startswith("categoria:"):
            dados["categoria"] = linha_limpa.split(":", 1)[1].strip()

        elif linha_limpa.lower().startswith("prioridade:"):
            dados["prioridade"] = linha_limpa.split(":", 1)[1].strip()

    return dados

# ============================================
# AGENTE RECEPÇÃO
# ============================================

recepcao_agent = Agent(
    id="agentRecepcao",
    name="Recepção",
    role="Triagem inicial de suporte técnico",

    instructions=[

        "Você é o agente de recepção de um sistema de suporte técnico.",
        "Você realiza apenas triagem inicial e NÃO resolve problemas.",

        "Seu objetivo é coletar informações suficientes para encaminhar o caso ao agente classificador.",
        "Faça no máximo 2 perguntas por interação, apenas se realmente necessário.",

        "Sempre responda no formato:",
        "1. Resumo do problema",
        "2. Fatos confirmados",
        "3. Perguntas (se necessário)",

        "Não repita perguntas já respondidas.",
        "Se o usuário já forneceu informações suficientes, NÃO faça novas perguntas.",
        "Evite perguntas desnecessárias.",
        "Prefira encaminhar rapidamente ao especialista.",

        "Quando o caso estiver compreendido, finalize com:",
        "PRONTO PARA ENCAMINHAMENTO.",

        "Se o contexto possuir STATUS: ENCAMINHAR IMEDIATAMENTE AO CLASSIFICADOR SEM FAZER PERGUNTAS:",
        "não faça perguntas.",
        "gere apenas o resumo final.",
        "encaminhe imediatamente ao classificador.",

        "Se esta for a 3ª interação:",
        "não faça perguntas.",

        "Você deve encerrar com:",
        "Estou encaminhando seu caso para análise técnica.",

        "Seja claro e direto."
    ],

    model=model
)

# ============================================
# AGENTE CLASSIFICADOR
# ============================================

classificador_agent = Agent(

    id="agentClassificador",

    name="Classificador",

    role="Classificação de chamados técnicos",

    instructions=[
        "Você é um agente classificador.",
        "Você NÃO conversa.",
        "Você NÃO faz perguntas.",
        "Você NÃO explica nada.",
        "Você deve responder SOMENTE no formato abaixo.",

        "Categoria: hardware | software | rede",
        "Prioridade: baixa | média | alta | crítica",
        "Especialista: técnico correspondente"
    ],

    markdown=False,

    model=model
)

# Parte do Jean:

# ============================================
# AGENTE ESPECIALISTA
# ============================================

especialista_agent = Agent(

    id="agentEspecialista",

    name="Especialista Técnico",

    role="Especialista em resolução de problemas técnicos",

    instructions=[
        "Você é um especialista técnico.",
        "Você recebe um problema já classificado.",
        "Use obrigatoriamente a tool buscar_solucao.",
        "Analise as causas prováveis do problema.",
        "Sugira soluções claras e organizadas.",
        "Seja técnico mas fácil de entender.",
        "Sempre responda em português do Brasil.",
        "Organize sua resposta em:",

        "1. Diagnóstico provável",
        "2. Possíveis causas",
        "3. Soluções recomendadas"
    ],

    tools=[
        buscar_solucao
    ],

    model=model
)

# ============================================
# AGENTE GERADOR
# ============================================

generator_agent = Agent(

    id="agentGenerator",

    name="Generator Agent",

    role="Transformar diagnóstico técnico em resposta amigável",

    instructions=[
        "Use linguagem simples.",
        "Evite termos técnicos difíceis.",
        "Explique o problema claramente.",
        "Organize em parágrafos.",
        "Use listas quando necessário.",
        "Nunca invente informações.",
        "Baseie-se apenas no diagnóstico recebido.",
        "Mantenha tom amigável.",
        "Sempre em português do Brasil."
    ],

    markdown=True,

    model=model
)

# ============================================
# MODELO DE REQUISIÇÃO
# ============================================

class Mensagem(BaseModel):
    session_id: str
    mensagem: str

# ============================================
# MEMÓRIA
# ============================================

sessions = {}

# ============================================
# HOME
# ============================================

@app.get("/")
def home():
    return {
        "status": "API Multiagente Online"
    }

# ============================================
# SUPORTE
# ============================================

@app.post("/suporte")
def suporte(dados: Mensagem):

    # cria sessão
    if dados.session_id not in sessions:

        sessions[dados.session_id] = {
            "contador": 0,
            "historico": []
        }

    session = sessions[dados.session_id]

    # histórico
    session["historico"].append(dados.mensagem)

    session["contador"] += 1

    contexto = "\n".join(session["historico"])

    # ========================================
    # DETECÇÃO DE PROBLEMA COMPLETO
    # ========================================

    mensagem_lower = dados.mensagem.lower()

    problema_completo = any(

        palavra in mensagem_lower

        for palavra in [
            "trava",
            "lento",
            "internet",
            "ram",
            "erro",
            "wifi",
            "não liga",
            "superaquece"
        ]
    )

    # ========================================
    # DECISÃO
    # ========================================

    encaminhar = (

        session["contador"] >= 3

        or problema_completo
    )

    # ========================================
    # CONTEXTO DE ENCAMINHAMENTO
    # ========================================

    if encaminhar:

        contexto += (
            "\n\n"
            "[STATUS: ENCAMINHAR IMEDIATAMENTE AO CLASSIFICADOR SEM FAZER PERGUNTAS]"
        )

    # ========================================
    # RECEPÇÃO
    # ========================================

    resposta_recepcao = recepcao_agent.run(contexto)

    # ========================================
    # CLASSIFICAÇÃO + ESPECIALISTA
    # ========================================

    if encaminhar:

        resposta_classificador = classificador_agent.run(
            resposta_recepcao.content
        )

        resposta_especialista = especialista_agent.run(
            f"""
            Histórico:
            {contexto}

            Classificação:
            {resposta_classificador.content}

            Use obrigatoriamente a tool buscar_solucao.
            """
        )

        dados_classificacao = extrair_dados_classificacao(
            resposta_classificador.content
        )

        dados_gerador = {
            "categoria": dados_classificacao["categoria"],
            "prioridade": dados_classificacao["prioridade"],
            "diagnostico": resposta_especialista.content,
            "solucoes": [
                "Seguir as recomendações apresentadas"
            ]
        }

        resposta_gerador = generator_agent.run(
            f"""
            Transforme o diagnóstico técnico abaixo em uma resposta amigável para o usuário.

            Dados de entrada:
            {json.dumps(dados_gerador, ensure_ascii=False, indent=2)}
            """
        )

        # ========================================
        # PARTE DO FABRICIO (AGENTE GERADOR)
        # ========================================
        

        # ====================================
        # SUPERVISOR
        # ====================================

        resultado_supervisor = supervisionar_fluxo({

            "problema_usuario": contexto,

            "categoria": resposta_classificador.content,

            "solucao_tecnica": resposta_especialista.content,

            "resposta_final": resposta_gerador.content
        })

        return {
            "recepcao": resposta_recepcao.content,
            "classificacao": resposta_classificador.content,
            "especialista": resposta_especialista.content,
            "gerador": resposta_gerador.content,
            "supervisor": {
                "status": resultado_supervisor["status"],

                "score": resultado_supervisor["score"],

                "analise": resultado_supervisor["analise_llm"]
            },

            "status": "RESOLVIDO"
        }

    # ========================================
    # TRIAGEM
    # ========================================

    return {
        "recepcao": resposta_recepcao.content,
        "classificacao": "Aguardando triagem inicial...",
        "status": "TRIAGEM"
    }

# ============================================
# AGNO OS
# ============================================

agent_os = AgentOS(
    agents=[
        recepcao_agent,
        classificador_agent,
        especialista_agent,
        generator_agent,
        supervisor_agent
    ]
)