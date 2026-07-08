import streamlit as st
import pandas as pd
import re
import io

# ==========================================
# CONFIGURAÇÕES INICIAIS E SEGURANÇA
# ==========================================
SENHA_DO_PAINEL = "senha123"

# Cola o link completo da tua planilha Google Sheets aqui:
URL_DA_PLANILHA = "https://docs.google.com/spreadsheets/d/1c0UKQiMhQdz1GPBQYC4q3SItdDxKNXKffVZF231Z8L4/edit?gid=79367712#gid=79367712"
# ==========================================

st.set_page_config(page_title="Painel de Telefonia", layout="wide", page_icon="📞")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    h1, h2, h3 { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #212529; }
    .stDataFrame { background-color: white; border-radius: 8px; padding: 5px; }
    div.stButton > button {
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.2s;
        width: 100%;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    </style>
""", unsafe_allow_html=True)


def criar_card_html(titulo, valor, cor_topo, info_extra=""):
    return f"""
    <div style="
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-top: 5px solid {cor_topo};
        border-radius: 8px;
        padding: 20px 15px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.04);
        margin-bottom: 15px;
        font-family: 'Segoe UI', Arial, sans-serif;
    ">
        <div style="color: #6c757d; font-size: 14px; font-weight: 600; margin-bottom: 8px; text-transform: uppercase;">{titulo}</div>
        <div style="color: #212529; font-size: 38px; font-weight: 700; margin-bottom: 4px;">{valor}</div>
        <div style="color: #868e96; font-size: 11px; font-weight: 500; line-height: 1.4;">{info_extra}</div>
    </div>
    """


# Tela de Login
def verificar_senha():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.write("")
        c1, c2, c3 = st.columns([1, 1.5, 1])
        with c2:
            st.markdown("<h2 style='text-align: center;'>🔒 Acesso Restrito</h2>", unsafe_allow_html=True)
            senha_digitada = st.text_input("Senha do Sistema:", type="password", placeholder="Digite a senha...")
            if st.button("Entrar no Painel"):
                if senha_digitada == SENHA_DO_PAINEL:
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("❌ Senha incorreta. Tente novamente.")
        st.stop()


verificar_senha()

# Inicializa as variáveis de sessão para as categorias manuais
if "triagem_manual" not in st.session_state:
    st.session_state["triagem_manual"] = {}
if "categorias_customizadas" not in st.session_state:
    st.session_state["categorias_customizadas"] = []


# ==========================================
# MOTOR DE CONEXÃO E CAPTURA DE DADOS
# ==========================================
def converter_link_sheets(url):
    try:
        if "docs.google.com/spreadsheets" in url:
            match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
            if match:
                return f"https://docs.google.com/spreadsheets/d/{match.group(1)}/export?format=xlsx"
        return url
    except:
        return url


if URL_DA_PLANILHA == "CONHEÇA_O_SEU_LINK_AQUI":
    st.info("💡 Por favor, configure o link da sua planilha na linha 12 do código.")
    st.stop()

try:
    url_exportacao = converter_link_sheets(URL_DA_PLANILHA)


    @st.cache_data(ttl=60)
    def puxar_todas_planilhas(url):
        return pd.read_excel(url, sheet_name=None)


    with st.spinner("🔄 Conectando ao Google Sheets e processando colunas..."):
        dicionario_planilhas = puxar_todas_planilhas(url_exportacao)

    nome_aba_principal = list(dicionario_planilhas.keys())[0]
    df = dicionario_planilhas[nome_aba_principal].copy()

    abas_cres = {nome: df_cre for nome, df_cre in dicionario_planilhas.items() if "CRE" in nome.upper()}

    # Padronização e Limpeza
    df.columns = df.columns.str.strip()
    df = df.astype(str).replace("nan", "")


    def limpar_texto(texto):
        texto = str(texto).lower()
        texto = re.sub(r'[áàâã]', 'a', texto)
        texto = re.sub(r'[éê]', 'e', texto)
        texto = re.sub(r'[í]', 'i', texto)
        texto = re.sub(r'[óôõ]', 'o', texto)
        texto = re.sub(r'[ú]', 'u', texto)
        texto = texto.replace('ç', 'c')
        return texto


    colunas_limpas = [limpar_texto(c) for c in df.columns.tolist()]


    def mapear_coluna(termos_chave):
        for original, limpa in zip(df.columns.tolist(), colunas_limpas):
            if any(t in limpa for t in termos_chave): return original
        return None


    col_escola = mapear_coluna(["nome da escola", "escola"])
    col_idt = mapear_coluna(["idt da escola", "idt"])
    col_cre = mapear_coluna(["numero da cre", "cre"])
    col_telefone = mapear_coluna(["telefone da escola para contato", "contato"])
    col_migracao = mapear_coluna(["realizou a migracao", "migracao para o uc4x"])
    col_portabilidade = mapear_coluna(["fez portabilidade", "portabilidade?"])
    col_recebeu_ip = mapear_coluna(["recebeu um aparelho", "aparelho de telefone ip"])
    col_funciona_ip = mapear_coluna(["instalado e funcionando", "funcionando"])
    col_acao_realizada = mapear_coluna(["qual acao a escola realizou", "acao a escola"])
    col_operadora = mapear_coluna(["qual a nova operadora", "operadora? (apenas cnpj)"])
    col_novo_num = mapear_coluna(["qual o novo numero", "novo numero de telefone"])
    col_obs = mapear_coluna(["descreva a situacao", "obs"])

    if col_idt: df[col_idt] = df[col_idt].str.replace(".0", "", regex=False)
    if col_cre: df[col_cre] = df[col_cre].str.replace(".0", "", regex=False)

    # ==========================================
    # PROCESSAMENTO DAS MÁSCARAS E REGRAS DE NEGÓCIO
    # ==========================================

    mask_migracao = df[col_acao_realizada].str.contains("migra", case=False,
                                                        na=False) if col_acao_realizada else pd.Series(False,
                                                                                                       index=df.index)
    if col_migracao: mask_migracao = mask_migracao | df[col_migracao].str.contains("sim", case=False, na=False)

    mask_portabilidade = df[col_acao_realizada].str.contains("portab", case=False,
                                                             na=False) if col_acao_realizada else pd.Series(False,
                                                                                                            index=df.index)
    if col_portabilidade: mask_portabilidade = mask_portabilidade | df[col_portabilidade].str.contains("sim",
                                                                                                       case=False,
                                                                                                       na=False)

    mask_cancelamento = df[col_acao_realizada].str.contains("cancel", case=False,
                                                            na=False) if col_acao_realizada else pd.Series(False,
                                                                                                           index=df.index)
    mask_outras = df[col_acao_realizada].str.contains("outr", case=False,
                                                      na=False) if col_acao_realizada else pd.Series(False,
                                                                                                     index=df.index)

    mask_ip_ok = df[col_funciona_ip].str.contains("sim", case=False, na=False) if col_funciona_ip else pd.Series(False,
                                                                                                                 index=df.index)
    mask_ip_nao_inst = (df[col_recebeu_ip].str.contains("sim", case=False, na=False)) & (
        ~df[col_funciona_ip].str.contains("sim", case=False,
                                          na=False)) if col_recebeu_ip and col_funciona_ip else pd.Series(False,
                                                                                                          index=df.index)
    mask_sem_ip = df[col_recebeu_ip].str.contains("não|nao", case=False, na=False) if col_recebeu_ip else pd.Series(
        False, index=df.index)
    mask_operadoras = (df[col_operadora] != "") & (df[col_operadora].str.strip() != "") if col_operadora else pd.Series(
        False, index=df.index)

    # Lista de destinos padrões fixos
    destinos_padroes = [
        "Migração (UC4X) + Telefone OK",
        "Migração (UC4X) + Sem Telefone",
        "Portabilidade + Telefone OK",
        "Portabilidade + Sem Telefone",
        "Processo de Cancelamento"
    ]

    # ------------------------------------------
    # APLICAÇÃO DO MOTOR DE TRIAGEM MANUAL (OVERRIDES)
    # ------------------------------------------
    for idx_linha, destino_escolhido in st.session_state["triagem_manual"].items():
        if idx_linha in df.index:
            # Reseta as marcas originais desta linha
            mask_migracao.loc[idx_linha] = False
            mask_portabilidade.loc[idx_linha] = False
            mask_cancelamento.loc[idx_linha] = False
            mask_outras.loc[idx_linha] = False

            # Aplica os booleanos apenas para os destinos padrões
            if destino_escolhido == "Migração (UC4X) + Telefone OK":
                mask_migracao.loc[idx_linha] = True
                mask_ip_ok.loc[idx_linha] = True
                mask_sem_ip.loc[idx_linha] = False
            elif destino_escolhido == "Migração (UC4X) + Sem Telefone":
                mask_migracao.loc[idx_linha] = True
                mask_sem_ip.loc[idx_linha] = True
                mask_ip_ok.loc[idx_linha] = False
            elif destino_escolhido == "Portabilidade + Telefone OK":
                mask_portabilidade.loc[idx_linha] = True
                mask_ip_ok.loc[idx_linha] = True
                mask_sem_ip.loc[idx_linha] = False
            elif destino_escolhido == "Portabilidade + Sem Telefone":
                mask_portabilidade.loc[idx_linha] = True
                mask_sem_ip.loc[idx_linha] = True
                mask_ip_ok.loc[idx_linha] = False
            elif destino_escolhido == "Processo de Cancelamento":
                mask_cancelamento.loc[idx_linha] = True

    # ------------------------------------------
    # CRIAÇÃO DA COLUNA VISUAL DE STATUS
    # ------------------------------------------
    df['Status'] = "⚪ Indefinido"
    df.loc[mask_outras, 'Status'] = "🟣 Outros"
    df.loc[mask_cancelamento, 'Status'] = "🔴 Cancelamento"
    df.loc[mask_portabilidade, 'Status'] = "🟢 Portabilidade"
    df.loc[mask_migracao, 'Status'] = "🟡 Migração"

    # Força a atualização do texto de status para refletir inclusive as categorias customizadas
    for idx_linha, destino_escolhido in st.session_state["triagem_manual"].items():
        if idx_linha in df.index:
            if destino_escolhido.startswith("Migração"):
                df.loc[idx_linha, 'Status'] = "🟡 Migração"
            elif destino_escolhido.startswith("Portabilidade"):
                df.loc[idx_linha, 'Status'] = "🟢 Portabilidade"
            elif destino_escolhido == "Processo de Cancelamento":
                df.loc[idx_linha, 'Status'] = "🔴 Cancelamento"
            else:
                # Se caiu aqui, é uma categoria que você criou manualmente!
                df.loc[idx_linha, 'Status'] = f"🔵 {destino_escolhido}"

    # Sub-contagens analíticas
    migra_com_ip = (mask_migracao & mask_ip_ok).sum()
    migra_sem_ip = (mask_migracao & mask_sem_ip).sum()
    porta_com_ip = (mask_portabilidade & mask_ip_ok).sum()
    porta_sem_ip = (mask_portabilidade & mask_sem_ip).sum()


    # ==========================================
    # JANELAS FLUTUANTES (MODAIS)
    # ==========================================

    @st.dialog("Tabela de Escolas", width="large")
    def abrir_tabela(titulo, df_filtrado, colunas_exibicao, chave_tipo="comum"):
        st.subheader(titulo)

        if chave_tipo == "outras_acoes":
            st.markdown("### 🛠️ Central de Triagem de Casos Excepcionais")

            # --- MÓDULO DE CRIAÇÃO DE CATEGORIAS ---
            with st.container(border=True):
                st.markdown("**➕ Criar Nova Categoria de Card**")
                cc1, cc2 = st.columns([3, 1])
                with cc1:
                    nova_categoria = st.text_input("Nome (ex: Aguardando Visita Técnica)", key="input_nova_cat",
                                                   label_visibility="collapsed")
                with cc2:
                    if st.button("Adicionar", use_container_width=True):
                        if nova_categoria and nova_categoria not in st.session_state[
                            "categorias_customizadas"] and nova_categoria not in destinos_padroes:
                            st.session_state["categorias_customizadas"].append(nova_categoria)
                            st.rerun()
            st.write("---")

            if df_filtrado.empty:
                st.success("🎉 Excelente! Todas as outras ações foram triadas e organizadas!")
                return

            todas_opcoes_dropdown = ["Selecione o destino..."] + destinos_padroes + st.session_state[
                "categorias_customizadas"]

            for index, row in df_filtrado.iterrows():
                nome_esc = row.get(col_escola, "Escola Não Identificada")
                id_esc = row.get(col_idt, "")
                obs_esc = row.get(col_obs, "Sem observações no formulário.")
                contato_esc = row.get(col_telefone, "Não informado")
                status_atual = row.get('Status', '')

                with st.expander(f"🏫 {nome_esc} (IDT: {id_esc}) - {status_atual}"):
                    c_info, c_acao = st.columns([3, 2])
                    with c_info:
                        st.write(f"**Contato:** {contato_esc}")
                        st.info(f"**Relato da Escola:**\n\n{obs_esc}")
                    with c_acao:
                        destino = st.selectbox(
                            "Enviar esta escola para:",
                            todas_opcoes_dropdown,
                            key=f"sel_{index}"
                        )

                        if st.button("Confirmar Envio ✔️", key=f"btn_envio_{index}"):
                            if destino != "Selecione o destino...":
                                st.session_state["triagem_manual"][index] = destino
                                st.success("Encaminhado com sucesso!")
                                st.rerun()
                            else:
                                st.warning("Por favor, selecione uma opção válida.")
            return

        # Visualização Padrão de Listas
        b1, b2 = st.columns([4, 1])
        with b1:
            pesquisa = st.text_input("🔍 Pesquisar na lista...", placeholder="Busque por nome, IDT ou CRE...")
            if pesquisa and col_escola:
                mask_pesquisa = (
                        df_filtrado[col_escola].str.contains(pesquisa, case=False, na=False) |
                        df_filtrado[col_idt].str.contains(pesquisa, case=False, na=False) |
                        df_filtrado[col_cre].str.contains(pesquisa, case=False, na=False)
                )
                df_filtrado = df_filtrado[mask_pesquisa]
        with b2:
            st.write("")
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_filtrado.to_excel(writer, index=False, sheet_name='PainelExportado')
            st.download_button("📥 Baixar Excel", data=output.getvalue(), file_name=f"{titulo}.xlsx",
                               use_container_width=True)

        st.dataframe(df_filtrado[colunas_exibicao], use_container_width=True, hide_index=True)


    @st.dialog("Detalhes das Coordenadorias (CREs)", width="large")
    def abrir_tabela_cres():
        st.subheader("Abas Consolidadas por CRE")
        if not abas_cres:
            st.warning("Nenhuma aba contendo 'CRE' no nome foi encontrada na planilha.")
            return

        cre_selecionada = st.selectbox("Escolha a CRE para carregar os ramais:", list(abas_cres.keys()))
        df_cre_atual = abas_cres[cre_selecionada].copy()
        df_cre_atual.columns = [c if "Unnamed" not in str(c) else "" for c in df_cre_atual.columns]
        st.dataframe(df_cre_atual, use_container_width=True, hide_index=True)


    cols_padrao = ['Status'] + [c for c in [col_escola, col_idt, col_cre, col_telefone, col_obs] if c is not None]
    cols_procergs = ['Status'] + [c for c in [col_escola, col_idt, col_novo_num, col_operadora] if c is not None]
    cols_op = ['Status'] + [c for c in [col_escola, col_operadora, col_novo_num, col_telefone] if c is not None]

    # ==========================================
    # INTERFACE PRINCIPAL - MATRIZ DE CARDS
    # ==========================================
    c_head, c_refresh, c_logout = st.columns([6, 1, 1])
    with c_head:
        st.markdown("<h1 style='margin:0;'>📞 Painel de Telefonia - Status Geral</h1>", unsafe_allow_html=True)
    with c_refresh:
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            puxar_todas_planilhas.clear()
            # Opcional: Se quiser que o botão limpar tudo (incluindo as customizadas criadas), descomente abaixo
            # st.session_state["triagem_manual"] = {}
            # st.session_state["categorias_customizadas"] = []
            st.rerun()
    with c_logout:
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()

    st.write("---")

    # --- LINHA DE CARDS 1 ---
    row1_1, row1_2, row1_3, row1_4, row1_5 = st.columns(5)
    with row1_1:
        st.markdown(criar_card_html("Total de Escolas", len(df), "#007bff", "Base unificada forms"),
                    unsafe_allow_html=True)
        if st.button("Ver Todas", key="btn_total"): abrir_tabela("Todas as Escolas (Geral)", df, cols_padrao)

    with row1_2:
        st.markdown(criar_card_html("Migração (UC4X)", mask_migracao.sum(), "#6c757d",
                                    f"📞 Com IP: {migra_com_ip} | ❌ Sem IP: {migra_sem_ip}"), unsafe_allow_html=True)
        if st.button("Ver Lista", key="btn_migra"): abrir_tabela("Escolas: Migração Realizada (UC4X)",
                                                                 df[mask_migracao], cols_padrao)

    with row1_3:
        st.markdown(criar_card_html("Portabilidade", mask_portabilidade.sum(), "#28a745",
                                    f"📞 Com IP: {porta_com_ip} | ❌ Sem IP: {porta_sem_ip}"), unsafe_allow_html=True)
        if st.button("Ver Lista", key="btn_porta"): abrir_tabela("Escolas: Portabilidade", df[mask_portabilidade],
                                                                 cols_padrao)

    with row1_4:
        st.markdown(criar_card_html("Telefone IP OK", mask_ip_ok.sum(), "#20c997", "Instalado e Ativo"),
                    unsafe_allow_html=True)
        if st.button("Ver Lista", key="btn_ipok"): abrir_tabela("Telefone IP Instalado e Funcionando", df[mask_ip_ok],
                                                                cols_padrao)

    with row1_5:
        st.markdown(criar_card_html("IP OK (Não Instalado)", mask_ip_nao_inst.sum(), "#ffc107", "Entregue físico"),
                    unsafe_allow_html=True)
        if st.button("Ver Lista", key="btn_ipni"): abrir_tabela("Telefone Entregue mas Não Instalado",
                                                                df[mask_ip_nao_inst], cols_padrao)

    # --- LINHA DE CARDS 2 ---
    row2_1, row2_2, row2_3, row2_4, row2_5 = st.columns(5)
    with row2_1:
        st.markdown(criar_card_html("Sem Telefone IP", mask_sem_ip.sum(), "#e83e8c", "Aguardando envio"),
                    unsafe_allow_html=True)
        if st.button("Ver Lista", key="btn_semip"): abrir_tabela("Escolas Sem Aparelho IP", df[mask_sem_ip],
                                                                 cols_padrao)

    with row2_2:
        st.markdown(criar_card_html("Coordenadorias", len(abas_cres), "#fd7e14", "Abas de CRE detectadas"),
                    unsafe_allow_html=True)
        if st.button("Ver Detalhes", key="btn_cre"): abrir_tabela_cres()

    with row2_3:
        st.markdown(criar_card_html("Cancelamento", mask_cancelamento.sum(), "#343a40", "Pedidos Oi"),
                    unsafe_allow_html=True)
        if st.button("Ver Lista", key="btn_canc"): abrir_tabela("Processos de Cancelamento", df[mask_cancelamento],
                                                                cols_padrao)

    with row2_4:
        st.markdown(criar_card_html("Outras Ações", mask_outras.sum(), "#6f42c1", "Requer triagem manual"),
                    unsafe_allow_html=True)
        if st.button("Ver Detalhes", key="btn_outras"): abrir_tabela("Triagem de Outras Ações", df[mask_outras],
                                                                     cols_padrao, chave_tipo="outras_acoes")

    with row2_5:
        st.markdown(criar_card_html("Dados para Procergs", "Ver", "#4b0082", "Mapeamento para Procergs"),
                    unsafe_allow_html=True)
        if st.button("Ver Lista", key="btn_procergs"): abrir_tabela("Dados Formatados - Procergs", df, cols_procergs)

    # --- LINHA DE CARDS 3 ---
    row3_1, _, _, _, _ = st.columns(5)
    with row3_1:
        st.markdown(criar_card_html("Info Operadoras", mask_operadoras.sum(), "#17a2b8", "Mapeamentos CNPJ"),
                    unsafe_allow_html=True)
        if st.button("Ver Detalhes", key="btn_operadoras"): abrir_tabela("Informações de Operadoras",
                                                                         df[mask_operadoras], cols_op)

    # --- SESSÃO DINÂMICA: CARDS CRIADOS MANUALMENTE ---
    if st.session_state["categorias_customizadas"]:
        st.write("---")
        st.markdown("<h3 style='margin:0; color:#17a2b8;'>🛠️ Categorias Personalizadas (Criadas por Você)</h3>",
                    unsafe_allow_html=True)
        st.write("")

        # Divide as categorias extras em linhas de 5 cartões para não quebrar o layout visual
        for i in range(0, len(st.session_state["categorias_customizadas"]), 5):
            cols_dinamicas = st.columns(5)
            lote_categorias = st.session_state["categorias_customizadas"][i:i + 5]

            for idx_cat, cat_nome in enumerate(lote_categorias):
                with cols_dinamicas[idx_cat]:
                    qtd_escolas_na_cat = (df['Status'] == f"🔵 {cat_nome}").sum()
                    st.markdown(criar_card_html(cat_nome, qtd_escolas_na_cat, "#0dcaf0", "Organizado via triagem"),
                                unsafe_allow_html=True)
                    if st.button("Ver Lista", key=f"btn_dinamico_{cat_nome}"):
                        abrir_tabela(f"Escolas: {cat_nome}", df[df['Status'] == f"🔵 {cat_nome}"], cols_padrao)

except Exception as e:
    st.error(f"🚨 Erro crítico ao carregar ou processar dados da planilha.")
    st.info(f"Detalhes técnicos: {e}")