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

st.set_page_config(page_title="Painel de Telefonia", layout="wide", page_icon="📞")

# --- ESTILIZAÇÃO CSS (RESPONSIVIDADE MELHORADA) ---
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
    /* Deixa os cards mais flexíveis e adapta ao espaço */
    .card-kpi {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.04);
        margin-bottom: 15px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .card-title { color: #6c757d; font-size: 13px; font-weight: 600; text-transform: uppercase; margin-bottom: 5px; }
    .card-valor { color: #212529; font-size: 34px; font-weight: 700; margin-bottom: 2px; }
    .card-info { color: #868e96; font-size: 11px; font-weight: 500; }
    </style>
""", unsafe_allow_html=True)

def criar_card_html(titulo, valor, cor_topo, info_extra=""):
    return f"""
    <div class="card-kpi" style="border-top: 5px solid {cor_topo};">
        <div class="card-title">{titulo}</div>
        <div class="card-valor">{valor}</div>
        <div class="card-info">{info_extra}</div>
    </div>
    """

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

if "triagem_manual" not in st.session_state:
    st.session_state["triagem_manual"] = {}
if "categorias_customizadas" not in st.session_state:
    st.session_state["categorias_customizadas"] = []

destinos_padroes = [
    "Migração (UC4X) + Telefone OK",
    "Migração (UC4X) + Sem Telefone",
    "Portabilidade + Telefone OK",
    "Portabilidade + Sem Telefone",
    "Processo de Cancelamento"
]

def converter_link_sheets(url):
    try:
        if "docs.google.com/spreadsheets" in url:
            match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
            if match: return f"https://docs.google.com/spreadsheets/d/{match.group(1)}/export?format=xlsx"
        return url
    except: return url

# ==========================================
# MOTOR DE DADOS OTIMIZADO (CACHE PESADO E CENTRALIZADO)
# ==========================================
# Ao esconder o processamento pesado aqui, o Streamlit executa a varredura da planilha
# de forma isolada, e não "trava" ao atualizar os botões.
@st.cache_data(ttl=60, show_spinner=False)
def carregar_e_processar_dados(url):
    dici = pd.read_excel(url, sheet_name=None)
    nome_principal = list(dici.keys())[0]
    df = dici[nome_principal].copy()
    abas_cres = {nome: df_cre for nome, df_cre in dici.items() if "CRE" in nome.upper()}

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

    cols = {
        "escola": mapear_coluna(["nome da escola", "escola"]),
        "idt": mapear_coluna(["idt da escola", "idt"]),
        "cre": mapear_coluna(["numero da cre", "cre"]),
        "telefone": mapear_coluna(["telefone da escola para contato", "contato"]),
        "migracao": mapear_coluna(["realizou a migracao", "migracao para o uc4x"]),
        "portabilidade": mapear_coluna(["fez portabilidade", "portabilidade?"]),
        "recebeu_ip": mapear_coluna(["recebeu um aparelho", "aparelho de telefone ip"]),
        "funciona_ip": mapear_coluna(["instalado e funcionando", "funcionando"]),
        "acao": mapear_coluna(["qual acao a escola realizou", "acao a escola"]),
        "operadora": mapear_coluna(["qual a nova operadora", "operadora? (apenas cnpj)"]),
        "novo_num": mapear_coluna(["qual o novo numero", "novo numero de telefone"]),
        "obs": mapear_coluna(["descreva a situacao", "obs"])
    }

    if cols["idt"]: df[cols["idt"]] = df[cols["idt"]].str.replace(".0", "", regex=False)
    if cols["cre"]: df[cols["cre"]] = df[cols["cre"]].str.replace(".0", "", regex=False)

    # Criação da estrutura base de máscaras
    m_migracao = df[cols["acao"]].str.contains("migra", case=False, na=False) if cols["acao"] else pd.Series(False, index=df.index)
    if cols["migracao"]: m_migracao = m_migracao | df[cols["migracao"]].str.contains("sim", case=False, na=False)

    m_porta = df[cols["acao"]].str.contains("portab", case=False, na=False) if cols["acao"] else pd.Series(False, index=df.index)
    if cols["portabilidade"]: m_porta = m_porta | df[cols["portabilidade"]].str.contains("sim", case=False, na=False)

    m_canc = df[cols["acao"]].str.contains("cancel", case=False, na=False) if cols["acao"] else pd.Series(False, index=df.index)
    m_outras = df[cols["acao"]].str.contains("outr", case=False, na=False) if cols["acao"] else pd.Series(False, index=df.index)

    m_ip_ok = df[cols["funciona_ip"]].str.contains("sim", case=False, na=False) if cols["funciona_ip"] else pd.Series(False, index=df.index)
    m_ip_nao_inst = (df[cols["recebeu_ip"]].str.contains("sim", case=False, na=False)) & (~df[cols["funciona_ip"]].str.contains("sim", case=False, na=False)) if cols["recebeu_ip"] and cols["funciona_ip"] else pd.Series(False, index=df.index)
    m_sem_ip = df[cols["recebeu_ip"]].str.contains("não|nao", case=False, na=False) if cols["recebeu_ip"] else pd.Series(False, index=df.index)
    
    m_operadoras = (df[cols["operadora"]] != "") & (df[cols["operadora"]].str.strip() != "") if cols["operadora"] else pd.Series(False, index=df.index)

    # Atribui o status visual bruto da planilha
    df['Status'] = "⚪ Indefinido"
    df.loc[m_outras, 'Status'] = "🟣 Outros"
    df.loc[m_canc, 'Status'] = "🔴 Cancelamento"
    df.loc[m_porta, 'Status'] = "🟢 Portabilidade"
    df.loc[m_migracao, 'Status'] = "🟡 Migração"

    masks = {
        "migracao": m_migracao, "portabilidade": m_porta, "cancelamento": m_canc, "outras": m_outras,
        "ip_ok": m_ip_ok, "ip_nao_inst": m_ip_nao_inst, "sem_ip": m_sem_ip, "operadoras": m_operadoras
    }

    return df, abas_cres, cols, masks

# ==========================================
# EXECUÇÃO PRINCIPAL
# ==========================================
if URL_DA_PLANILHA == "CONHEÇA_O_SEU_LINK_AQUI":
    st.info("💡 Por favor, configure o link da sua planilha no topo do código.")
    st.stop()

try:
    url_exportacao = converter_link_sheets(URL_DA_PLANILHA)
    
    with st.spinner("🔄 Conectando ao Google Sheets e analisando rede..."):
        df_base, abas_cres, cols, masks_base = carregar_e_processar_dados(url_exportacao)
    
    # Criamos cópias instantâneas para não mexer no cache protegido. 
    # Isso faz os cliques de botões responderem sem nenhum delay.
    df = df_base.copy()
    m_migracao = masks_base["migracao"].copy()
    m_porta = masks_base["portabilidade"].copy()
    m_canc = masks_base["cancelamento"].copy()
    m_outras = masks_base["outras"].copy()
    m_ip_ok = masks_base["ip_ok"].copy()
    m_sem_ip = masks_base["sem_ip"].copy()
    m_ip_nao_inst = masks_base["ip_nao_inst"].copy()
    m_operadoras = masks_base["operadoras"].copy()

    # Aplica as regras de override (Triagem) super rápido
    for idx_linha, destino in st.session_state["triagem_manual"].items():
        if idx_linha in df.index:
            # Reseta os originais dessa linha
            m_migracao.loc[idx_linha] = m_porta.loc[idx_linha] = m_canc.loc[idx_linha] = m_outras.loc[idx_linha] = False
            
            if destino == destinos_padroes[0]: # Migração + OK
                m_migracao.loc[idx_linha], m_ip_ok.loc[idx_linha], m_sem_ip.loc[idx_linha] = True, True, False
            elif destino == destinos_padroes[1]: # Migração + Sem IP
                m_migracao.loc[idx_linha], m_sem_ip.loc[idx_linha], m_ip_ok.loc[idx_linha] = True, True, False
            elif destino == destinos_padroes[2]: # Porta + OK
                m_porta.loc[idx_linha], m_ip_ok.loc[idx_linha], m_sem_ip.loc[idx_linha] = True, True, False
            elif destino == destinos_padroes[3]: # Porta + Sem IP
                m_porta.loc[idx_linha], m_sem_ip.loc[idx_linha], m_ip_ok.loc[idx_linha] = True, True, False
            elif destino == destinos_padroes[4]: # Cancelamento
                m_canc.loc[idx_linha] = True

            # Colore visualmente
            if destino.startswith("Migração"): df.loc[idx_linha, 'Status'] = "🟡 Migração"
            elif destino.startswith("Portabilidade"): df.loc[idx_linha, 'Status'] = "🟢 Portabilidade"
            elif destino == "Processo de Cancelamento": df.loc[idx_linha, 'Status'] = "🔴 Cancelamento"
            else: df.loc[idx_linha, 'Status'] = f"🔵 {destino}"

    # Recálculo das frações analíticas
    migra_com_ip = (m_migracao & m_ip_ok).sum()
    migra_sem_ip = (m_migracao & m_sem_ip).sum()
    porta_com_ip = (m_porta & m_ip_ok).sum()
    porta_sem_ip = (m_porta & m_sem_ip).sum()

    # ==========================================
    # MODAIS (JANELAS FLUTUANTES)
    # ==========================================
    @st.dialog("Tabela de Escolas", width="large")
    def abrir_tabela(titulo, df_filtrado, colunas_exibicao, chave_tipo="comum"):
        st.subheader(titulo)
        
        if chave_tipo == "outras_acoes":
            st.markdown("### 🛠️ Central de Triagem")
            with st.container(border=True):
                st.markdown("**➕ Criar Nova Categoria**")
                cc1, cc2 = st.columns([3, 1])
                with cc1: nova_cat = st.text_input("Nome", key="input_nova_cat", label_visibility="collapsed", placeholder="Ex: Aguardando Visita")
                with cc2:
                    if st.button("Adicionar", use_container_width=True):
                        if nova_cat and nova_cat not in st.session_state["categorias_customizadas"] and nova_cat not in destinos_padroes:
                            st.session_state["categorias_customizadas"].append(nova_cat)
                            st.rerun()
            st.write("---")

            if df_filtrado.empty:
                st.success("🎉 Todas as ações manuais foram triadas!")
                return

            todas_opcoes = ["Selecione..."] + destinos_padroes + st.session_state["categorias_customizadas"]
            for index, row in df_filtrado.iterrows():
                with st.expander(f"🏫 {row.get(cols['escola'], 'N/A')} - {row.get('Status', '')}"):
                    c_info, c_acao = st.columns([3, 2])
                    with c_info:
                        st.write(f"**Contato:** {row.get(cols['telefone'], 'N/A')}")
                        st.info(f"**Relato:**\n{row.get(cols['obs'], '')}")
                    with c_acao:
                        destino = st.selectbox("Encaminhar para:", todas_opcoes, key=f"sel_{index}")
                        if st.button("Confirmar ✔️", key=f"btn_envio_{index}"):
                            if destino != "Selecione...":
                                st.session_state["triagem_manual"][index] = destino
                                st.rerun()
            return # Trava a execução do restante da janela de Outras Ações

        # Modo de visualização de listas comuns
        b1, b2 = st.columns([4, 1])
        with b1:
            pesquisa = st.text_input("🔍 Buscar escola...", placeholder="Busque por nome ou IDT...")
            if pesquisa and cols['escola']:
                mask_pesquisa = (
                        df_filtrado[cols['escola']].str.contains(pesquisa, case=False, na=False) |
                        df_filtrado[cols['idt']].str.contains(pesquisa, case=False, na=False)
                )
                df_filtrado = df_filtrado[mask_pesquisa]
        with b2:
            st.write("")
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_filtrado.to_excel(writer, index=False, sheet_name='Export')
            st.download_button("📥 Baixar Excel", data=output.getvalue(), file_name=f"{titulo}.xlsx", use_container_width=True)

        st.dataframe(df_filtrado[colunas_exibicao], use_container_width=True, hide_index=True)

    @st.dialog("Detalhes das Coordenadorias (CREs)", width="large")
    def abrir_tabela_cres():
        st.subheader("Abas Consolidadas")
        if not abas_cres: st.warning("Nenhuma CRE encontrada no arquivo raiz."); return
        cre_selecionada = st.selectbox("Escolha a base para inspecionar:", list(abas_cres.keys()))
        df_cre_atual = abas_cres[cre_selecionada].copy()
        df_cre_atual.columns = [c if "Unnamed" not in str(c) else "" for c in df_cre_atual.columns]
        st.dataframe(df_cre_atual, use_container_width=True, hide_index=True)

    # Identificadores de colunas protegidos
    cols_padrao = ['Status'] + [c for c in [cols['escola'], cols['idt'], cols['cre'], cols['telefone'], cols['obs']] if c is not None]
    cols_procergs = ['Status'] + [c for c in [cols['escola'], cols['idt'], cols['novo_num'], cols['operadora']] if c is not None]
    cols_op = ['Status'] + [c for c in [cols['escola'], cols['operadora'], cols['novo_num'], cols['telefone']] if c is not None]

    # ==========================================
    # DESENHO DA INTERFACE PRINCIPAL
    # ==========================================
    c_head, c_refresh, c_logout = st.columns([6, 1, 1])
    with c_head:
        st.markdown("<h1 style='margin:0;'>📞 Painel de Telefonia - Status Geral</h1>", unsafe_allow_html=True)
    with c_refresh:
        if st.button("🔄 Atualizar Base", use_container_width=True):
            carregar_e_processar_dados.clear()
            st.rerun()
    with c_logout:
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()

    st.write("---")

    # MATRIZ 1
    r1_cols = st.columns(5)
    with r1_cols[0]:
        st.markdown(criar_card_html("Total", len(df), "#007bff", "Base unificada"), unsafe_allow_html=True)
        if st.button("Todas", key="btn_total"): abrir_tabela("Geral", df, cols_padrao)
    with r1_cols[1]:
        st.markdown(criar_card_html("Migração", m_migracao.sum(), "#6c757d", f"Com IP: {migra_com_ip} | Sem: {migra_sem_ip}"), unsafe_allow_html=True)
        if st.button("Lista", key="btn_migra"): abrir_tabela("Migração", df[m_migracao], cols_padrao)
    with r1_cols[2]:
        st.markdown(criar_card_html("Portabilidade", m_porta.sum(), "#28a745", f"Com IP: {porta_com_ip} | Sem: {porta_sem_ip}"), unsafe_allow_html=True)
        if st.button("Lista", key="btn_porta"): abrir_tabela("Portabilidade", df[m_porta], cols_padrao)
    with r1_cols[3]:
        st.markdown(criar_card_html("IP OK", m_ip_ok.sum(), "#20c997", "Instalado/Ativo"), unsafe_allow_html=True)
        if st.button("Lista", key="btn_ipok"): abrir_tabela("Telefone IP OK", df[m_ip_ok], cols_padrao)
    with r1_cols[4]:
        st.markdown(criar_card_html("IP (Não Inst)", m_ip_nao_inst.sum(), "#ffc107", "Aparelho Entregue"), unsafe_allow_html=True)
        if st.button("Lista", key="btn_ipni"): abrir_tabela("Não Instalado", df[m_ip_nao_inst], cols_padrao)

    st.write("") 
    
    # MATRIZ 2
    r2_cols = st.columns(5)
    with r2_cols[0]:
        st.markdown(criar_card_html("Sem IP", m_sem_ip.sum(), "#e83e8c", "Aguardando"), unsafe_allow_html=True)
        if st.button("Lista", key="btn_semip"): abrir_tabela("Sem Aparelho", df[m_sem_ip], cols_padrao)
    with r2_cols[1]:
        st.markdown(criar_card_html("CREs", len(abas_cres), "#fd7e14", "Abas detectadas"), unsafe_allow_html=True)
        if st.button("Ver", key="btn_cre"): abrir_tabela_cres()
    with r2_cols[2]:
        st.markdown(criar_card_html("Cancelamento", m_canc.sum(), "#343a40", "Pedidos Oi"), unsafe_allow_html=True)
        if st.button("Lista", key="btn_canc"): abrir_tabela("Cancelamento", df[m_canc], cols_padrao)
    with r2_cols[3]:
        st.markdown(criar_card_html("Outras", m_outras.sum(), "#6f42c1", "Triagem manual"), unsafe_allow_html=True)
        if st.button("Ver", key="btn_outras"): abrir_tabela("Triagem", df[m_outras], cols_padrao, "outras_acoes")
    with r2_cols[4]:
        st.markdown(criar_card_html("Procergs", "Ver", "#4b0082", "Mapeamento"), unsafe_allow_html=True)
        if st.button("Lista", key="btn_procergs"): abrir_tabela("Procergs", df, cols_procergs)

    # MATRIZ 3
    r3_cols = st.columns(5)
    with r3_cols[0]:
        st.markdown(criar_card_html("Operadoras", m_operadoras.sum(), "#17a2b8", "Mapeamentos"), unsafe_allow_html=True)
        if st.button("Ver", key="btn_op"): abrir_tabela("Operadoras", df[m_operadoras], cols_op)

    # MATRIZ DINÂMICA (CARDS CUSTOMIZADOS)
    if st.session_state["categorias_customizadas"]:
        st.write("---")
        st.markdown("<h3 style='margin:0; color:#17a2b8;'>🛠️ Categorias Personalizadas</h3>", unsafe_allow_html=True)
        st.write("")

        for i in range(0, len(st.session_state["categorias_customizadas"]), 5):
            cols_dinamicas = st.columns(5)
            lote = st.session_state["categorias_customizadas"][i:i+5]
            for idx, cat_nome in enumerate(lote):
                with cols_dinamicas[idx]:
                    qtd = (df['Status'] == f"🔵 {cat_nome}").sum()
                    st.markdown(criar_card_html(cat_nome, qtd, "#0dcaf0", "Organizado via triagem"), unsafe_allow_html=True)
                    if st.button("Lista", key=f"btn_dinamico_{cat_nome}"):
                        abrir_tabela(cat_nome, df[df['Status'] == f"🔵 {cat_nome}"], cols_padrao)

except Exception as e:
    st.error(f"🚨 Erro crítico ao processar o painel.")
    st.info(f"Detalhes técnicos: {e}")
