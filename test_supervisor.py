from supervisor_agent import supervisionar_fluxo

dados_teste = {
    "problema_usuario": "Meu computador está sem internet.",
    "categoria": "Rede",
    "solucao_tecnica": "Reinicie o roteador e verifique os cabos.",
    "resposta_final": """
    Olá! Identificamos um possível problema de conexão.
    Reinicie o roteador, verifique os cabos de rede
    e tente conectar novamente.
    """
}

resultado = supervisionar_fluxo(dados_teste)

print(resultado)