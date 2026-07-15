import streamlit as st
import pandas as pd
import re
import io
import unicodedata
import os
import requests
import urllib3

# Desativa os avisos de segurança no terminal ao ignorar o certificado do Proxy
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 🔌 GERENCIADOR DINÂMICO DE PROXY (SEGURO)
# ==========================================
if "proxy_tipo" not in st.session_state:
    st.session_state["proxy_tipo"] = "Padrão (Sem Autenticação)"

if st.session_state["proxy_tipo"] == "Autenticado (SEDUC)":
    user = st.session_state.get("proxy_user", "")
    pwd = st.session_state.get("proxy_password", "")
    if user and pwd:
        os.environ["HTTP_PROXY"] = f"http://{user}:{pwd}@proxy.seduc.intra.rs.gov.br:3128"
        os.environ["HTTPS_PROXY"] = f"http://{user}:{pwd}@proxy.seduc.intra.rs.gov.br:3128"
elif st.session_state["proxy_tipo"] == "Sem Proxy (Conexão Direta)":
    os.environ.pop("HTTP_PROXY", None)
    os.environ.pop("HTTPS_PROXY", None)
else:
    os.environ["HTTP_PROXY"] = "http://proxy.seduc.intra.rs.gov.br:3128"
    os.environ["HTTPS_PROXY"] = "http://proxy.seduc.intra.rs.gov.br:3128"

os.environ["NO_PROXY"] = "localhost,127.0.0.1,localhost:8501,127.0.0.1:8501"

# ==========================================
# CONFIGURAÇÕES DA APLICAÇÃO
# ==========================================
SENHA_DO_PAINEL = "senha123"
URL_DA_PLANILHA = "https://docs.google.com/spreadsheets/d/1c0UKQiMhQdz1GPBQYC4q3SItdDxKNXKffVZF231Z8L4/edit?gid=79367712#gid=79367712"

st.set_page_config(page_title="Painel de Telefonia", layout="wide", page_icon="📞")

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

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.write("")
    _, c2, _ = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<h2 style='text-align: center;'>🔒 Acesso Restrito</h2>", unsafe_allow_html=True)
        senha_digitada = st.text_input("Senha do Sistema:", type="password", placeholder="Digite a senha...")
        if st.button("Entrar no Painel") and senha_digitada == SENHA_DO_PAINEL:
            st.session_state["autenticado"] = True
            st.rerun()
        elif senha_digitada:
            st.error("❌ Senha incorreta. Tente novamente.")
    st.stop()

if "triagem_manual" not in st.session_state:
    st.session_state["triagem_manual"] = {}
if "categorias_customizadas" not in st.session_state:
    st.session_state["categorias_customizadas"] = []

def converter_link_sheets(url):
    try:
        if "docs.google.com/spreadsheets" in url:
            match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
            if match:
                return f"https://docs.google.com/spreadsheets/d/{match.group(1)}/export?format=xlsx"
        return url
    except:
        return url

# ==========================================
# NOVO MOTOR DE DOWNLOAD BLINDADO
# ==========================================
@st.cache_data(ttl=60)
def puxar_todas_planilhas(url, tipo_proxy, user, pwd):
    # Constrói o dicionário de proxy para a requisição
    proxies_dict = {}
    if tipo_proxy == "Autenticado (SEDUC)":
        proxy_str = f"http://{user}:{pwd}@proxy.seduc.intra.rs.gov.br:3128"
        proxies_dict = {"http": proxy_str, "https": proxy_str}
    elif tipo_proxy == "Padrão (Sem Autenticação)":
        proxy_str = "http://proxy.seduc.intra.rs.gov.br:3128"
        proxies_dict = {"http": proxy_str, "https": proxy_str}

    try:
        # verify=False é o grande segredo aqui. Ele ignora o bloqueio de SSL do Proxy!
        resposta = requests.get(url, proxies=proxies_dict, verify=False, timeout=20)
        
        if resposta.status_code == 407:
            raise Exception("ERRO 407: O Proxy bloqueou a tentativa. Usuário ou senha incorretos.")
        
        resposta.raise_for_status()
        
        # Passa o arquivo baixado em memória para o Pandas ler
        return pd.read_excel(io.BytesIO(resposta.content), sheet_name=None)
    except requests.exceptions.ProxyError:
        raise Exception("Erro de Proxy: O servidor proxy recusou a conexão.")
    except requests.exceptions.ConnectionError:
        raise Exception("Erro de Conexão: Não foi possível alcançar o Google Sheets. Verifique o Proxy.")

try:
    url_exportacao = converter_link_sheets(URL_DA_PLANILHA)

    with st.spinner("🔄 Conectando aos servidores do Google passando pelo proxy da SEDUC..."):
        dicionario_planilhas = puxar_todas_planilhas(
            url_exportacao, 
            st.session_state["proxy_tipo"], 
            st.session_state.get("proxy_user", ""), 
            st.session_state.get("proxy_password", "")
        )

    # Processamento dos Dados
    nome_aba_principal = list(dicionario_planilhas.keys())[0]
    df = dicionario_planilhas[nome_aba_principal].copy()
    abas_cres = {nome: df_cre for nome, df_cre in dicionario_planilhas.items() if "CRE" in nome.upper() and nome != nome_aba_principal}

    df.columns = df.columns.str.strip()
    df = df.astype(str).replace("nan", "")

    colunas_limpas = [unicodedata.normalize('NFKD', str(c)).encode('ascii', 'ignore').decode('utf-8').lower().strip() for c in df.columns]

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

    get_mask = lambda col, pattern: df[col].str.contains(pattern, case=False, na=False) if col else pd.Series(False, index=df.index)

    mask_migracao = get_mask(col_acao_realizada, "migra") | (get_mask(col_migracao, "sim") if col_migracao else False)
    mask_portabilidade = get_mask(col_acao_realizada, "portab") | (get_mask(col_portabilidade, "sim") if col_portabilidade else False)
    mask_cancelamento = get_mask(col_acao_realizada, "cancel")
    mask_outras = get_mask(col_acao_realizada, "outr") & ~mask_migracao & ~mask_portabilidade & ~mask_cancelamento

    mask_ip_ok = get_mask(col_funciona_ip, "sim")
    mask_ip_nao_inst = get_mask(col_recebeu_ip, "sim") & ~get_mask(col_funciona_ip, "sim")
    mask_sem_ip = get_mask(col_recebeu_ip, "não|nao")
    mask_operadoras = (df[col_operadora].str.strip() != "") if col_operadora else pd.Series(False, index=df.index)

    destinos_padroes = ["Migração (UC4X) + Telefone OK", "Migração (UC4X) + Sem Telefone", "Portabilidade + Telefone OK", "Portabilidade + Sem Telefone", "Processo de Cancelamento"]

    for idx_linha, destino_escolhido in st.session_state["triagem_manual"].items():
        if idx_linha in df.index:
            for m in [mask_migracao, mask_portabilidade, mask_cancelamento, mask_outras]: m.loc[idx_linha] = False
            if destino_escolhido == "Migração (UC4X) + Telefone OK": mask_migracao.loc[idx_linha], mask_ip_ok.loc[idx_linha], mask_sem_ip.loc[idx_linha] = True, True, False
            elif destino_escolhido == "Migração (UC4X) + Sem Telefone": mask_migracao.loc[idx_linha], mask_sem_ip.loc[idx_linha], mask_ip_ok.loc[idx_linha] = True, True, False
            elif destino_escolhido == "Portabilidade + Telefone OK": mask_portabilidade.loc[idx_linha], mask_ip_ok.loc[idx_linha], mask_sem_ip.loc[idx_linha] = True, True, False
            elif destino_escolhido == "Portabilidade + Sem Telefone": mask_portabilidade.loc[idx_linha], mask_sem_ip.loc[idx_linha], mask_ip_ok.loc[idx_linha] = True, True, False
            elif destino_escolhido == "Processo de Cancelamento": mask_cancelamento.loc[idx_linha] = True

    df['Status'] = "⚪ Indefinido"
    df.loc[mask_outras, 'Status'] = "🟣 Outros"
    df.loc[mask_cancelamento, 'Status'] = "🔴 Cancelamento"
    df.loc[mask_portabilidade, 'Status'] = "🟢 Portabilidade"
    df.loc[mask_migracao, 'Status'] = "🟡 Migração"

    for idx_linha, destino in st.session_state["triagem_manual"].items():
        if idx_linha in df.index:
            if destino.startswith("Migração"): df.loc[idx_linha, 'Status'] = "🟡 Migração"
            elif destino.startswith("Portabilidade"): df.loc[idx_linha, 'Status'] = "🟢 Portabilidade"
            elif destino == "Processo de Cancelamento": df.loc[idx_linha, 'Status'] = "🔴 Cancelamento"
            else: df.loc[idx_linha, 'Status'] = f"🔵 {destino}"

    migra_com_ip = (mask_migracao & mask_ip_ok).sum()
    migra_sem_ip = (mask_migracao & mask_sem_ip).sum()
    porta_com_ip = (mask_portabilidade & mask_ip_ok).sum()
    porta_sem_ip = (mask_portabilidade & mask_sem_ip).sum()

    @st.dialog("Tabela de Escolas", width="large")
    def abrir_tabela(titulo, df_filtrado, colunas_exibicao, chave_tipo="comum"):
        st.subheader(titulo)
        if chave_tipo == "outras_acoes":
            st.markdown("### 🛠️ Central de Triagem")
            with st.container(border=True):
                cc1, cc2 = st.columns([3, 1])
                nova_categoria = cc1.text_input("Nova Categoria:", key="input_nova_cat", label_visibility="collapsed")
                if cc2.button("Adicionar Categoria"):
                    if nova_categoria and nova_categoria not in st.session_state["categorias_customizadas"] and nova_categoria not in destinos_padroes:
                        st.session_state["categorias_customizadas"].append(nova_categoria)
                        st.rerun()
            st.write("---")
            if df_filtrado.empty: return st.success("🎉 Tudo triado!")

            todas_opcoes = ["Selecione o destino..."] + destinos_padroes + st.session_state["categorias_customizadas"]
            for index, row in df_filtrado.iterrows():
                with st.expander(f"🏫 {row.get(col_escola, 'Sem Nome')} - {row.get('Status', '')}"):
                    c_info, c_acao = st.columns([3, 2])
                    c_info.write(f"**Contato:** {row.get(col_telefone, '')}")
                    c_info.info(f"**Relato:** {row.get(col_obs, '')}")
                    destino = c_acao.selectbox("Enviar para:", todas_opcoes, key=f"sel_{index}")
                    if c_acao.button("Confirmar ✔️", key=f"btn_{index}") and destino != "Selecione o destino...":
                        st.session_state["triagem_manual"][index] = destino
                        st.rerun()
            return

        b1, b2 = st.columns([4, 1])
        pesquisa = b1.text_input("🔍 Pesquisar...")
        if pesquisa:
            mask_pesq = pd.Series(False, index=df_filtrado.index)
            for c in [col_escola, col_idt, col_cre]:
                if c: mask_pesq |= df_filtrado[c].str.contains(pesquisa, case=False, na=False)
            df_filtrado = df_filtrado[mask_pesq]

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer: df_filtrado.to_excel(writer, index=False)
        b2.download_button("📥 Baixar Excel", data=output.getvalue(), file_name=f"{titulo}.xlsx")
        st.dataframe(df_filtrado[colunas_exibicao], use_container_width=True, hide_index=True)

    @st.dialog("Detalhes CREs", width="large")
    def abrir_tabela_cres():
        if not abas_cres: return st.warning("Nenhuma aba CRE encontrada.")
        cre_selecionada = st.selectbox("Escolha a CRE:", list(abas_cres.keys()))
        df_cre_atual = abas_cres[cre_selecionada].copy()
        
        novas_cols = []
        for c in df_cre_atual.columns:
            nome = "" if "Unnamed" in str(c) else str(c)
            while nome in novas_cols: nome += " "
            novas_cols.append(nome)
        df_cre_atual.columns = novas_cols

        if len(df_cre_atual) > 0 and len(df_cre_atual.columns) > 2:
            valor_linha_2 = df_cre_atual.iloc[0, 1]
            df_cre_atual.iloc[:, 1] = ""
            df_cre_atual.iloc[0, 1] = valor_linha_2

            col_soft = next((c for c in df_cre_atual.columns if "soft" in str(c).lower()), None)
            if col_soft:
                for idx in df_cre_atual.index:
                    val = str(df_cre_atual.loc[idx, col_soft]).strip().lower()
                    tem = False
                    if val and val not in ["0", "0.0", "não", "nao", "", "nan"]:
                        try: tem = float(val) >= 1
                        except: tem = True
                    if not tem: df_cre_atual.iloc[idx, 2] = ""

        st.dataframe(df_cre_atual.dropna(how='all').astype(str), use_container_width=True, hide_index=True)

    cols_padrao = ['Status'] + [c for c in [col_escola, col_idt, col_cre, col_telefone, col_obs] if c is not None]
    cols_procergs = ['Status'] + [c for c in [col_escola, col_idt, col_novo_num, col_operadora] if c is not None]
    cols_op = ['Status'] + [c for c in [col_escola, col_operadora, col_novo_num, col_telefone] if c is not None]

    c_head, c_refresh, c_logout = st.columns([6, 1, 1])
    c_head.markdown("<h1 style='margin:0;'>📞 Painel de Telefonia</h1>", unsafe_allow_html=True)
    if c_refresh.button("🔄 Atualizar"): puxar_todas_planilhas.clear(); st.rerun()
    if c_logout.button("🚪 Sair"): st.session_state["autenticado"] = False; st.rerun()
    st.write("---")

    cards = [
        {"title": "Total Escolas", "val": len(df), "color": "#007bff", "info": "Base", "df": df, "cols": cols_padrao, "key": "tot", "t": "c"},
        {"title": "Migração (UC4X)", "val": mask_migracao.sum(), "color": "#6c757d", "info": f"📞 {migra_com_ip} | ❌ {migra_sem_ip}", "df": df[mask_migracao], "cols": cols_padrao, "key": "mig", "t": "c"},
        {"title": "Portabilidade", "val": mask_portabilidade.sum(), "color": "#28a745", "info": f"📞 {porta_com_ip} | ❌ {porta_sem_ip}", "df": df[mask_portabilidade], "cols": cols_padrao, "key": "por", "t": "c"},
        {"title": "Telefone IP OK", "val": mask_ip_ok.sum(), "color": "#20c997", "info": "Ativo", "df": df[mask_ip_ok], "cols": cols_padrao, "key": "ipo", "t": "c"},
        {"title": "IP (Não Instalado)", "val": mask_ip_nao_inst.sum(), "color": "#ffc107", "info": "Físico", "df": df[mask_ip_nao_inst], "cols": cols_padrao, "key": "ipni", "t": "c"},
        {"title": "Sem Telefone IP", "val": mask_sem_ip.sum(), "color": "#e83e8c", "info": "Aguardando", "df": df[mask_sem_ip], "cols": cols_padrao, "key": "sip", "t": "c"},
        {"title": "Coordenadorias", "val": len(abas_cres), "color": "#fd7e14", "info": "Abas CRE", "key": "cre", "t": "cre"},
        {"title": "Cancelamento", "val": mask_cancelamento.sum(), "color": "#343a40", "info": "Oi", "df": df[mask_cancelamento], "cols": cols_padrao, "key": "can", "t": "c"},
        {"title": "Outras Ações", "val": mask_outras.sum(), "color": "#6f42c1", "info": "Triagem", "df": df[mask_outras], "cols": cols_padrao, "key": "out", "t": "o"},
        {"title": "Procergs", "val": "Ver", "color": "#4b0082", "info": "Mapeamento", "df": df, "cols": cols_procergs, "key": "pro", "t": "c"},
        {"title": "Operadoras", "val": mask_operadoras.sum(), "color": "#17a2b8", "info": "CNPJ", "df": df[mask_operadoras], "cols": cols_op, "key": "ope", "t": "c"}
    ]

    for i in range(0, len(cards), 5):
        cols = st.columns(5)
        for idx, c in enumerate(cards[i:i+5]):
            with cols[idx]:
                st.markdown(criar_card_html(c["title"], c["val"], c["color"], c["info"]), unsafe_allow_html=True)
                if c["t"] == "c" and st.button("Ver Lista", key=f"b_{c['key']}"): abrir_tabela(c["title"], c["df"], c["cols"])
                elif c["t"] == "o" and st.button("Triagem", key=f"b_{c['key']}"): abrir_tabela(c["title"], c["df"], c["cols"], "outras_acoes")
                elif c["t"] == "cre" and st.button("Ver Abas", key=f"b_{c['key']}"): abrir_tabela_cres()

    if st.session_state["categorias_customizadas"]:
        st.write("---")
        st.markdown("<h3>🛠️ Categorias Personalizadas</h3>", unsafe_allow_html=True)
        for i in range(0, len(st.session_state["categorias_customizadas"]), 5):
            cols_din = st.columns(5)
            for idx, cat in enumerate(st.session_state["categorias_customizadas"][i:i+5]):
                with cols_din[idx]:
                    qtd = (df['Status'] == f"🔵 {cat}").sum()
                    st.markdown(criar_card_html(cat, qtd, "#0dcaf0"), unsafe_allow_html=True)
                    if st.button("Ver Lista", key=f"b_din_{cat}"): abrir_tabela(cat, df[df['Status'] == f"🔵 {cat}"], cols_padrao)

except Exception as e:
    st.error("🚨 O Proxy bloqueou a conexão ou as credenciais estão inválidas.")
    
    with st.container(border=True):
        st.subheader("⚙️ Tentar Nova Conexão")
        tipo = st.selectbox("Modo:", ["Padrão (Sem Autenticação)", "Autenticado (SEDUC)", "Sem Proxy (Conexão Direta)"], key="tmp_proxy")
        
        if tipo == "Autenticado (SEDUC)":
            u = st.text_input("Usuário do Windows (Seduc):", value=st.session_state.get("proxy_user", ""))
            p = st.text_input("Senha do Windows (Seduc):", type="password", value=st.session_state.get("proxy_password", ""))
            
        if st.button("💾 Reconectar", use_container_width=True):
            st.session_state["proxy_tipo"] = tipo
            if tipo == "Autenticado (SEDUC)":
                st.session_state["proxy_user"] = u
                st.session_state["proxy_password"] = p
            puxar_todas_planilhas.clear()
            st.rerun()
            
    st.info(f"Erro reportado: {e}")
