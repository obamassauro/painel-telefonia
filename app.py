import streamlit as st
import pandas as pd
import re
import io
import unicodedata

# ==========================================
# CONFIGURAÇÕES INICIAIS E SEGURANÇA
# ==========================================
SENHA_DO_PAINEL = "senha123"
URL_DA_PLANILHA = "https://docs.google.com/spreadsheets/d/1c0UKQiMhQdz1GPBQYC4q3SItdDxKNXKffVZF231Z8L4/edit?gid=79367712#gid=79367712"

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


# Autenticação de Acesso
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


try:
    url_exportacao = converter_link_sheets(URL_DA_PLANILHA)


    @st.cache_data(ttl=60)
    def puxar_todas_planilhas(url):
        return pd.read_excel(url, sheet_name=None)


    with st.spinner("🔄 Conectando ao Google Sheets e processando colunas..."):
        dicionario_planilhas = puxar_todas_planilhas(url_exportacao)

    nome_aba_principal = list(dicionario_planilhas.keys())[0]
    df = dicionario_planilhas[nome_aba_principal].copy()

    # Mapeia as CREs ignorando a aba principal
    abas_cres = {nome: df_cre for nome, df_cre in dicionario_planilhas.items() if "CRE" in nome.upper() and nome != nome_aba_principal}

    # Padronização e Limpeza Automatizada das Colunas (Unicode)
    df.columns = df.columns.str.strip()
    df = df.astype(str).replace("nan", "")

    colunas_limpas = [
        unicodedata.normalize('NFKD', str(c)).encode('ascii', 'ignore').decode('utf-8').lower().strip()
        for c in df.columns
    ]


    def mapear_coluna(termos_chave):
        for original, limpa in zip(df.columns.tolist(), colunas_limpas):
            if any(t in limpa for t in termos_chave):
                return original
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
    get_mask = lambda col, pattern: df[col].str.contains(pattern, case=False, na=False) if col else pd.Series(False, index=df.index)

    mask_migracao = get_mask(col_acao_realizada, "migra")
    if col_migracao: mask_migracao = mask_migracao | get_mask(col_migracao, "sim")

    mask_portabilidade = get_mask(col_acao_realizada, "portab")
    if col_portabilidade: mask_portabilidade = mask_portabilidade | get_mask(col_portabilidade, "sim")

    mask_cancelamento = get_mask(col_acao_realizada, "cancel")
    mask_outras = get_mask(col_acao_realizada, "outr") & ~mask_migracao & ~mask_portabilidade & ~mask_cancelamento

    mask_ip_ok = get_mask(col_funciona_ip, "sim")
    mask_ip_nao_inst = get_mask(col_recebeu_ip, "sim") & ~get_mask(col_funciona_ip, "sim")
    mask_sem_ip = get_mask(col_recebeu_ip, "não|nao")
    mask_operadoras = (df[col_operadora].str.strip() != "") if col_operadora else pd.Series(False, index=df.index)

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
            mask_migracao.loc[idx_linha] = False
            mask_portabilidade.loc[idx_linha] = False
            mask_cancelamento.loc[idx_linha] = False
            mask_outras.loc[idx_linha] = False

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

    for idx_linha, destino_escolhido in st.session_state["triagem_manual"].items():
        if idx_linha in df.index:
            if destino_escolhido.startswith("Migração"):
                df.loc[idx_linha, 'Status'] = "🟡 Migração"
            elif destino_escolhido.startswith("Portabilidade"):
                df.loc[idx_linha, 'Status'] = "🟢 Portabilidade"
            elif destino_escolhido == "Processo de Cancelamento":
                df.loc[idx_linha, 'Status'] = "🔴 Cancelamento"
            else:
                df.loc[idx_linha, 'Status'] = f"🔵 {destino_escolhido}"

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
            with st.container(border=True):
                st.markdown("**➕ Criar Nova Categoria de Card**")
                cc1, cc2 = st.columns([3, 1])
                nova_categoria = cc1.text_input("Nome (ex: Aguardando Visita Técnica)", key="input_nova_cat", label_visibility="collapsed")
                if cc2.button("Adicionar", use_container_width=True):
                    if nova_categoria and nova_categoria not in st.session_state["categorias_customizadas"] and nova_categoria not in destinos_padroes:
                        st.session_state["categorias_customizadas"].append(nova_categoria)
                        st.rerun()
            st.write("---")

            if df_filtrado.empty:
                st.success("🎉 Excelente! Todas as outras ações foram triadas e organizadas!")
                return

            todas_opcoes_dropdown = ["Selecione o destino..."] + destinos_padroes + st.session_state["categorias_customizadas"]

            for index, row in df_filtrado.iterrows():
                nome_esc = row.get(col_escola, "Escola Não Identificada")
                id_esc = row.get(col_idt, "")
                obs_esc = row.get(col_obs, "Sem observações no formulário.")
                contato_esc = row.get(col_telefone, "Não informado")
                status_atual = row.get('Status', '')

                with st.expander(f"🏫 {nome_esc} (IDT: {id_esc}) - {status_atual}"):
                    c_info, c_acao = st.columns([3, 2])
                    c_info.write(f"**Contato:** {contato_esc}")
                    c_info.info(f"**Relato da Escola:**\n\n{obs_esc}")
                    destino = c_acao.selectbox("Enviar esta escola para:", todas_opcoes_dropdown, key=f"sel_{index}")
                    if c_acao.button("Confirmar Envio ✔️", key=f"btn_envio_{index}"):
                        if destino != "Selecione o destino...":
                            st.session_state["triagem_manual"][index] = destino
                            st.success("Encaminhado com sucesso!")
                            st.rerun()
                        else:
                            st.warning("Por favor, selecione uma opção válida.")
            return

        # Visualização Padrão de Listas
        b1, b2 = st.columns([4, 1])
        pesquisa = b1.text_input("🔍 Pesquisar na lista...", placeholder="Busque por nome, IDT ou CRE...")
        if pesquisa:
            mask_pesquisa = pd.Series(False, index=df_filtrado.index)
            for c in [col_escola, col_idt, col_cre]:
                if c: mask_pesquisa |= df_filtrado[c].str.contains(pesquisa, case=False, na=False)
            df_filtrado = df_filtrado[mask_pesquisa]

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_filtrado.to_excel(writer, index=False, sheet_name='PainelExportado')
        b2.write("")
        b2.download_button("📥 Baixar Excel", data=output.getvalue(), file_name=f"{titulo}.xlsx", use_container_width=True)

        st.dataframe(df_filtrado[colunas_exibicao], use_container_width=True, hide_index=True)


    @st.dialog("Detalhes das Coordenadorias (CREs)", width="large")
    def abrir_tabela_cres():
        st.subheader("Abas Consolidadas por CRE")
        if not abas_cres:
            st.warning("Nenhuma aba contendo 'CRE' no nome foi encontrada na planilha.")
            return

        cre_selecionada = st.selectbox("Escolha a CRE para carregar os ramais:", list(abas_cres.keys()))
        df_cre_atual = abas_cres[cre_selecionada].copy()
        
        # Tratamento de colunas vazias e mescladas
        novas_cols = []
        for c in df_cre_atual.columns:
            nome = "" if "Unnamed" in str(c) else str(c)
            while nome in novas_cols:
                nome += " "
            novas_cols.append(nome)
        df_cre_atual.columns = novas_cols

        # ----------------------------------------------------
        # 🛠️ APLICAÇÃO DAS NOVAS REGRAS DE LIMPEZA PARA AS CRES
        # ----------------------------------------------------
        if len(df_cre_atual) > 0 and len(df_cre_atual.columns) > 2:
            # Regra 1: Na coluna B (Índice 1), só precisamos do dado da Linha 2 (Índice 0 no pandas)
            valor_linha_2 = df_cre_atual.iloc[0, 1]
            df_cre_atual.iloc[:, 1] = ""  # Limpa a coluna B inteira
            df_cre_atual.iloc[0, 1] = valor_linha_2  # Restaura apenas na Linha 2 (Pandas Index 0)

            # Regra 2: Na coluna C (Índice 2), Ramal/Nome só aparecem se houver >= 1 softphone na linha
            # Procuramos dinamicamente a coluna de softphones
            col_softphone = None
            for col in df_cre_atual.columns:
                if "soft" in str(col).lower():
                    col_softphone = col
                    break
            
            if col_softphone is not None:
                for idx in df_cre_atual.index:
                    val_soft = str(df_cre_atual.loc[idx, col_softphone]).strip().lower()
                    
                    tem_softphone = False
                    # Verifica se o valor indica que existe 1 ou mais softphones ativos
                    if val_soft and val_soft not in ["0", "0.0", "não", "nao", "", "nan"]:
                        try:
                            # Se for numérico, valida se é pelo menos 1
                            if float(val_soft) >= 1:
                                tem_softphone = True
                        except ValueError:
                            # Se for texto afirmativo (ex: "Sim", "Ativo"), assume verdadeiro
                            tem_softphone = True
                    
                    # Se NÃO tiver softphone, limpa as informações de ramal e nome na Coluna C (Índice 2)
                    if not tem_softphone:
                        df_cre_atual.iloc[idx, 2] = ""

        # Remove linhas completamente nulas que possam ter sobrado
        df_cre_atual = df_cre_atual.dropna(how='all')

        st.dataframe(df_cre_atual.astype(str), use_container_width=True, hide_index=True)


    cols_padrao = ['Status'] + [c for c in [col_escola, col_idt, col_cre, col_telefone, col_obs] if c is not None]
    cols_procergs = ['Status'] + [c for c in [col_escola, col_idt, col_novo_num, col_operadora] if c is not None]
    cols_op = ['Status'] + [c for c in [col_escola, col_operadora, col_novo_num, col_telefone] if c is not None]

    # ==========================================
    # INTERFACE PRINCIPAL - MATRIZ DE CARDS
    # ==========================================
    c_head, c_refresh, c_logout = st.columns([6, 1, 1])
    c_head.markdown("<h1 style='margin:0;'>📞 Painel de Telefonia - Status Geral</h1>", unsafe_allow_html=True)
    
    if c_refresh.button("🔄 Atualizar Dados", use_container_width=True):
        puxar_todas_planilhas.clear()
        st.rerun()
    if c_logout.button("🚪 Sair", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()

    st.write("---")

    # Mapeamento Dinâmico de Cartões
    cards = [
        {"title": "Total de Escolas", "val": len(df), "color": "#007bff", "info": "Base unificada forms", "df_filt": df, "cols_exib": cols_padrao, "key": "total", "type": "comum"},
        {"title": "Migração (UC4X)", "val": mask_migracao.sum(), "color": "#6c757d", "info": f"📞 Com IP: {migra_com_ip} | ❌ Sem IP: {migra_sem_ip}", "df_filt": df[mask_migracao], "cols_exib": cols_padrao, "key": "migra", "type": "comum"},
        {"title": "Portabilidade", "val": mask_portabilidade.sum(), "color": "#28a745", "info": f"📞 Com IP: {porta_com_ip} | ❌ Sem IP: {porta_sem_ip}", "df_filt": df[mask_portabilidade], "cols_exib": cols_padrao, "key": "porta", "type": "comum"},
        {"title": "Telefone IP OK", "val": mask_ip_ok.sum(), "color": "#20c997", "info": "Instalado e Ativo", "df_filt": df[mask_ip_ok], "cols_exib": cols_padrao, "key": "ipok", "type": "comum"},
        {"title": "IP OK (Não Instalado)", "val": mask_ip_nao_inst.sum(), "color": "#ffc107", "info": "Entregue físico", "df_filt": df[mask_ip_nao_inst], "cols_exib": cols_padrao, "key": "ipni", "type": "comum"},
        {"title": "Sem Telefone IP", "val": mask_sem_ip.sum(), "color": "#e83e8c", "info": "Aguardando envio", "df_filt": df[mask_sem_ip], "cols_exib": cols_padrao, "key": "semip", "type": "comum"},
        {"title": "Coordenadorias", "val": len(abas_cres), "color": "#fd7e14", "info": "Abas de CRE detectadas", "key": "cre", "type": "cre"},
        {"title": "Cancelamento", "val": mask_cancelamento.sum(), "color": "#343a40", "info": "Pedidos Oi", "df_filt": df[mask_cancelamento], "cols_exib": cols_padrao, "key": "canc", "type": "comum"},
        {"title": "Outras Ações", "val": mask_outras.sum(), "color": "#6f42c1", "info": "Requer triagem manual", "df_filt": df[mask_outras], "cols_exib": cols_padrao, "key": "outras", "type": "outras_acoes"},
        {"title": "Dados para Procergs", "val": "Ver", "color": "#4b0082", "info": "Mapeamento para Procergs", "df_filt": df, "cols_exib": cols_procergs, "key": "procergs", "type": "comum"},
        {"title": "Info Operadoras", "val": mask_operadoras.sum(), "color": "#17a2b8", "info": "Mapeamentos CNPJ", "df_filt": df[mask_operadoras], "cols_exib": cols_op, "key": "operadoras", "type": "comum"}
    ]

    # Grelha de 5 Colunas
    for i in range(0, len(cards), 5):
        cols_grid = st.columns(5)
        for idx_col, card in enumerate(cards[i:i+5]):
            with cols_grid[idx_col]:
                st.markdown(criar_card_html(card["title"], card["val"], card["color"], card["info"]), unsafe_allow_html=True)
                if card["type"] == "comum":
                    rotulo = "Ver Todas" if card["key"] == "total" else "Ver Lista"
                    if st.button(rotulo, key=f"btn_{card['key']}"):
                        abrir_tabela(card["title"], card["df_filt"], card["cols_exib"])
                elif card["type"] == "outras_acoes":
                    if st.button("Ver Detalhes", key=f"btn_{card['key']}"):
                        abrir_tabela(card["title"], card["df_filt"], card["cols_exib"], chave_tipo="outras_acoes")
                elif card["type"] == "cre":
                    if st.button("Ver Detalhes", key=f"btn_{card['key']}"):
                        abrir_tabela_cres()

    # --- SESSÃO DINÂMICA: CARDS CRIADOS MANUALMENTE ---
    if st.session_state["categorias_customizadas"]:
        st.write("---")
        st.markdown("<h3 style='margin:0; color:#17a2b8;'>🛠️ Categorias Personalizadas (Criadas por Você)</h3>", unsafe_allow_html=True)
        st.write("")

        for i in range(0, len(st.session_state["categorias_customizadas"]), 5):
            cols_dinamicas = st.columns(5)
            lote_categorias = st.session_state["categorias_customizadas"][i:i + 5]

            for idx_cat, cat_nome in enumerate(lote_categorias):
                with cols_dinamicas[idx_cat]:
                    qtd_escolas_na_cat = (df['Status'] == f"🔵 {cat_nome}").sum()
                    st.markdown(criar_card_html(cat_nome, qtd_escolas_na_cat, "#0dcaf0", "Organizado via triagem"), unsafe_allow_html=True)
                    if st.button("Ver Lista", key=f"btn_dinamico_{cat_nome}"):
                        abrir_tabela(f"Escolas: {cat_nome}", df[df['Status'] == f"🔵 {cat_nome}"], cols_padrao)

except Exception as e:
    st.error(f"🚨 Erro crítico ao carregar ou processar dados da planilha.")
    st.info(f"Detalhes técnicos: {e}")
