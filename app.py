from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import json
import datetime
from functools import wraps
from waitress import serve
import requests
import math

app = Flask(__name__)
app.secret_key = 'chave_secreta_muito_segura'

# Arquivos de dados
USUARIOS_FILE = "usuarios.json"
PASSAGENS_FILE = "passagens.json"
NOTIFICACOES_FILE = "notificacoes.json"

def enviar_whatsapp_notificacao(operadores, passagem_info):
    """Envia WhatsApp via API local para operadores notificados"""
    try:
        usuarios = carregar_usuarios()
        mensagens_enviadas = 0
        
        for username in operadores:
            if username in usuarios and usuarios[username].get('whatsapp'):
                user_whatsapp = usuarios[username]['whatsapp']
                user_name = usuarios[username]['nome_completo']
                
                # Formata o número (remove caracteres especiais)
                numero_whatsapp = ''.join(filter(str.isdigit, user_whatsapp))
                
                mensagem = f"""🚨 *NOVA PASSAGEM DE TURNO* 🚨

Olá *{user_name}*, foi registrada uma nova passagem de turno:

📍 *Regional:* {passagem_info['regional']}
🕒 *Turno:* {passagem_info['turno']}
📅 *Data do Plantão:* {passagem_info['data_plantao']}
👤 *Registrado por:* {passagem_info['registrado_por']}

📋 *Informações:*
{passagem_info['informacoes']}

_Esta é uma mensagem automática do Sistema de Passagens_"""
                
                # Envia para API local (venom-bot ou similar)
                payload = {
                    'number': f'55{numero_whatsapp}',  # Formato Brasil
                    'message': mensagem
                }
                
                try:
                    # Tenta enviar via API local
                    response = requests.post(
                        'http://localhost:3000/send-message', 
                        json=payload, 
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        print(f"✅ WhatsApp enviado para {user_name} ({user_whatsapp})")
                        mensagens_enviadas += 1
                    else:
                        print(f"❌ Erro API WhatsApp: {response.text}")
                        
                except requests.exceptions.ConnectionError:
                    print("⚠️  Serviço de WhatsApp não está rodando na porta 3000")
                except Exception as e:
                    print(f"❌ Erro ao enviar WhatsApp: {e}")
        
        return mensagens_enviadas > 0
                    
    except Exception as e:
        print(f"❌ Erro geral WhatsApp: {e}")
        return False

def carregar_usuarios():
    try:
        with open(USUARIOS_FILE, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
            if not conteudo:
                print(f"Arquivo {USUARIOS_FILE} está vazio")
                return {"admin": {"senha": "admin123", "nivel": "admin", "nome_completo": "Administrador do Sistema", "email": "admin@empresa.com", "telefone": "", "whatsapp": ""}}
            usuarios = json.loads(conteudo)
            
            # Garante que todos os usuários tenham os novos campos
            for username, info in usuarios.items():
                if 'email' not in info:
                    info['email'] = f"{username}@empresa.com"
                if 'telefone' not in info:
                    info['telefone'] = ""
                if 'whatsapp' not in info:
                    info['whatsapp'] = ""
            
            return usuarios
            
    except FileNotFoundError:
        print(f"Arquivo {USUARIOS_FILE} não encontrado, criando padrão")
        return {"admin": {"senha": "admin123", "nivel": "admin", "nome_completo": "Administrador do Sistema", "email": "admin@empresa.com", "telefone": "", "whatsapp": ""}}
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar {USUARIOS_FILE}: {e}")
        return {"admin": {"senha": "admin123", "nivel": "admin", "nome_completo": "Administrador do Sistema", "email": "admin@empresa.com", "telefone": "", "whatsapp": ""}}
    except Exception as e:
        print(f"Erro inesperado ao carregar {USUARIOS_FILE}: {e}")
        return {"admin": {"senha": "admin123", "nivel": "admin", "nome_completo": "Administrador do Sistema", "email": "admin@empresa.com", "telefone": "", "whatsapp": ""}}

def carregar_passagens():
    try:
        with open(PASSAGENS_FILE, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
            if not conteudo:
                print(f"Arquivo {PASSAGENS_FILE} está vazio")
                return []
            
            passagens = json.loads(conteudo)
            
            # Garante que todas as passagens tenham nome_completo
            usuarios = carregar_usuarios()
            for passagem in passagens:
                if 'nome_completo' not in passagem:
                    usuario = passagem.get('usuario')
                    if usuario in usuarios:
                        passagem['nome_completo'] = usuarios[usuario]['nome_completo']
                    else:
                        passagem['nome_completo'] = usuario  # Fallback para o username
            
            return passagens
            
    except FileNotFoundError:
        print(f"Arquivo {PASSAGENS_FILE} não encontrado, criando lista vazia")
        return []
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar {PASSAGENS_FILE}: {e}")
        return []
    except Exception as e:
        print(f"Erro inesperado ao carregar {PASSAGENS_FILE}: {e}")
        return []

def carregar_notificacoes():
    try:
        with open(NOTIFICACOES_FILE, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
            if not conteudo:
                print(f"Arquivo {NOTIFICACOES_FILE} está vazio")
                return {}
            return json.loads(conteudo)
    except FileNotFoundError:
        print(f"Arquivo {NOTIFICACOES_FILE} não encontrado, criando dicionário vazio")
        return {}
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar {NOTIFICACOES_FILE}: {e}")
        return {}
    except Exception as e:
        print(f"Erro inesperado ao carregar {NOTIFICACOES_FILE}: {e}")
        return {}

def salvar_usuarios(usuarios):
    try:
        with open(USUARIOS_FILE, 'w', encoding='utf-8') as f:
            json.dump(usuarios, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar {USUARIOS_FILE}: {e}")

def salvar_passagens(passagens):
    try:
        with open(PASSAGENS_FILE, 'w', encoding='utf-8') as f:
            json.dump(passagens, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar {PASSAGENS_FILE}: {e}")

def salvar_notificacoes(notificacoes):
    try:
        with open(NOTIFICACOES_FILE, 'w', encoding='utf-8') as f:
            json.dump(notificacoes, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar {NOTIFICACOES_FILE}: {e}")

def converter_data_iso_para_br(data_iso):
    """Converte data de YYYY-MM-DD para DD/MM/YYYY"""
    try:
        data_obj = datetime.datetime.strptime(data_iso, '%Y-%m-%d')
        return data_obj.strftime('%d/%m/%Y')
    except ValueError:
        return data_iso

def parse_data_para_ordenacao(data_str):
    """Converte string de data para objeto datetime para ordenação"""
    try:
        # Tenta converter do formato DD/MM/YYYY (formato BR exibido)
        if '/' in data_str:
            return datetime.datetime.strptime(data_str, '%d/%m/%Y')
        # Tenta converter do formato YYYY-MM-DD (formato input date)
        elif '-' in data_str:
            return datetime.datetime.strptime(data_str, '%Y-%m-%d')
        else:
            return datetime.datetime.min
    except ValueError:
        print(f"Erro ao converter data: {data_str}")
        return datetime.datetime.min

def carregar_passagens_ordenadas():
    """Carrega passagens ordenadas pelo ID (mais recente primeiro)"""
    passagens = carregar_passagens()
    
    # DEBUG: Mostra as passagens ANTES da ordenação
    print("=== ANTES DA ORDENAÇÃO ===")
    for p in passagens:
        print(f"ID: {p.get('id')} - Data: {p.get('data_plantao')} - Turno: {p.get('turno')}")
    
    # Ordena por ID DESC (mais recente primeiro)
    passagens.sort(key=lambda x: x.get('id', 0), reverse=True)
    
    # DEBUG: Mostra as passagens DEPOIS da ordenação
    print("=== DEPOIS DA ORDENAÇÃO ===")
    for p in passagens:
        print(f"ID: {p.get('id')} - Data: {p.get('data_plantao')} - Turno: {p.get('turno')}")
    print("="*50)
    
    return passagens

def obter_estatisticas_regionais():
    """Obtém estatísticas por regional para o dashboard"""
    passagens = carregar_passagens()
    
    # Contagem por regional
    regional_leste = len([p for p in passagens if p.get('regional') == 'Leste'])
    regional_centro = len([p for p in passagens if p.get('regional') == 'Centro'])
    regional_oeste = len([p for p in passagens if p.get('regional') == 'Oeste'])
    
    return {
        'regional_leste': regional_leste,
        'regional_centro': regional_centro,
        'regional_oeste': regional_oeste
    }

def adicionar_notificacao(operadores, passagem_id, titulo, criado_por):
    """Adiciona notificação para os operadores selecionados"""
    notificacoes = carregar_notificacoes()
    
    for operador in operadores:
        if operador not in notificacoes:
            notificacoes[operador] = []
        
        notificacoes[operador].append({
            'id': len(notificacoes[operador]) + 1,
            'passagem_id': passagem_id,
            'titulo': titulo,
            'criado_por': criado_por,
            'data': datetime.datetime.now().strftime('%d/%m/%Y %H:%M'),
            'lida': False
        })
    
    salvar_notificacoes(notificacoes)

def paginar_dados(dados, pagina=1, itens_por_pagina=10):
    """Função para paginar qualquer lista de dados"""
    total_itens = len(dados)
    total_paginas = math.ceil(total_itens / itens_por_pagina)
    
    # DEBUG DETALHADO
    print(f"🔍 PAGINAÇÃO DETALHADA:")
    print(f"   Total de itens: {total_itens}")
    print(f"   Itens por página: {itens_por_pagina}")
    print(f"   Cálculo: {total_itens} / {itens_por_pagina} = {total_itens / itens_por_pagina}")
    print(f"   Total de páginas (math.ceil): {total_paginas}")
    
    # Ajusta a página se estiver fora do range
    pagina = max(1, min(pagina, total_paginas))
    
    # Calcula índices de início e fim
    inicio = (pagina - 1) * itens_por_pagina
    fim = inicio + itens_por_pagina
    
    print(f"   Índices: [{inicio}:{fim}]")
    print(f"   Itens nesta página: {len(dados[inicio:fim])}")
    
    # Retorna os dados da página atual e informações de paginação
    return {
        'itens': dados[inicio:fim],
        'pagina_atual': pagina,
        'total_paginas': total_paginas,
        'total_itens': total_itens,
        'itens_por_pagina': itens_por_pagina,
        'inicio': inicio + 1,
        'fim': min(fim, total_itens)
    }

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        if session.get('nivel') != 'admin':
            flash('Acesso restrito para administradores!', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_now():
    """Injeta a data/hora atual em todos os templates"""
    return {'now': datetime.datetime.now}

@app.context_processor
def inject_notificacoes():
    """Injeta o número de notificações não lidas em todos os templates"""
    if 'usuario' in session:
        notificacoes = carregar_notificacoes()
        minhas_notificacoes = notificacoes.get(session['usuario'], [])
        nao_lidas = sum(1 for n in minhas_notificacoes if not n['lida'])
        return {'notificacoes_nao_lidas': nao_lidas}
    return {'notificacoes_nao_lidas': 0}

@app.context_processor
def inject_notificacoes_data():
    """Injeta as notificações do usuário atual em todos os templates"""
    if 'usuario' in session:
        notificacoes = carregar_notificacoes()
        minhas_notificacoes = notificacoes.get(session['usuario'], [])
        
        # Ordena por data (mais recente primeiro) e pega as não lidas
        minhas_notificacoes.sort(key=lambda x: datetime.datetime.strptime(x['data'], '%d/%m/%Y %H:%M'), reverse=True)
        notificacoes_nao_lidas = [n for n in minhas_notificacoes if not n['lida']]
        notificacoes_nao_lidas_preview = notificacoes_nao_lidas[:5]  # Apenas 5 primeiras
        
        return {
            'notificacoes_nao_lidas': len(notificacoes_nao_lidas),
            'notificacoes_nao_lidas_lista': notificacoes_nao_lidas_preview,
            'minhas_notificacoes': minhas_notificacoes
        }
    return {
        'notificacoes_nao_lidas': 0,
        'notificacoes_nao_lidas_lista': [],
        'minhas_notificacoes': []
    }

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d/%m/%Y %H:%M'):
    if isinstance(value, str):
        return value
    return value.strftime(format)

@app.route('/')
def index():
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    usuarios = carregar_usuarios()
    
    if request.method == 'POST':
        # Verifica se o campo 'username' existe no formulário
        username = request.form.get('username', '').lower()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Usuário e senha são obrigatórios!', 'error')
            return render_template('login.html')
        
        if username in usuarios and usuarios[username]['senha'] == password:
            session['usuario'] = username
            session['nome_completo'] = usuarios[username]['nome_completo']
            session['nivel'] = usuarios[username]['nivel']
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha inválidos!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    passagens = carregar_passagens_ordenadas()  # Agora ordenadas por ID DESC
    estatisticas = obter_estatisticas_regionais()
    
    # Filtra por regional (já vem ordenado)
    passagens_leste = [p for p in passagens if p.get('regional') == 'Leste']
    passagens_oeste = [p for p in passagens if p.get('regional') == 'Oeste']
    passagens_centro = [p for p in passagens if p.get('regional') == 'Centro']
    
    # Últimas 5 passagens (já estão ordenadas, pega as primeiras)
    ultimas_passagens = passagens[:5]
    
    return render_template('dashboard.html', 
                         passagens_leste=passagens_leste,
                         passagens_oeste=passagens_oeste,
                         passagens_centro=passagens_centro,
                         ultimas_passagens=ultimas_passagens,
                         estatisticas=estatisticas)

@app.route('/ultimas_passagens')
@login_required
def ultimas_passagens():
    passagens = carregar_passagens_ordenadas()  # Já ordenadas por ID DESC
    return render_template('passagens.html', 
                         passagens=passagens,
                         titulo="Últimas Passagens")

@app.route('/passagens')
@login_required
def listar_passagens():
    # DEBUG IMEDIATO - verifica se a rota está sendo chamada
    print("🎯 ROTA /passagens ACESSADA!")
    
    # Parâmetros de paginação
    pagina = request.args.get('pagina', 1, type=int)
    itens_por_pagina = request.args.get('itens_por_pagina', 10, type=int)
    
    print(f"📄 Parâmetros: página={pagina}, itens_por_pagina={itens_por_pagina}")
    
    # Carrega todas as passagens ordenadas
    passagens_todas = carregar_passagens_ordenadas()
    print(f"📊 Total de passagens carregadas: {len(passagens_todas)}")
    
    # Aplica paginação
    dados_paginados = paginar_dados(passagens_todas, pagina, itens_por_pagina)
    
    print(f"🔢 Paginação: {dados_paginados['pagina_atual']}/{dados_paginados['total_paginas']}")
    print(f"📋 Itens na página atual: {len(dados_paginados['itens'])}")
    
    return render_template('passagens.html', 
                         passagens=dados_paginados['itens'],
                         pagina_atual=dados_paginados['pagina_atual'],
                         total_paginas=dados_paginados['total_paginas'],
                         total_passagens=dados_paginados['total_itens'],
                         itens_por_pagina=dados_paginados['itens_por_pagina'],
                         titulo="Todas as Passagens")

@app.route('/passagens_regionais/<regional>')
@login_required
def passagens_regionais(regional):
    # Parâmetros de paginação
    pagina = request.args.get('pagina', 1, type=int)
    itens_por_pagina = request.args.get('itens_por_pagina', 10, type=int)
    
    passagens = carregar_passagens_ordenadas()  # Já ordenadas por ID DESC
    passagens_filtradas = [p for p in passagens if p.get('regional') == regional]
    
    # Aplica paginação
    dados_paginados = paginar_dados(passagens_filtradas, pagina, itens_por_pagina)
    
    return render_template('passagens.html', 
                         passagens=dados_paginados['itens'],
                         pagina_atual=dados_paginados['pagina_atual'],
                         total_paginas=dados_paginados['total_paginas'],
                         total_passagens=dados_paginados['total_itens'],
                         itens_por_pagina=dados_paginados['itens_por_pagina'],
                         titulo=f"Passagens - Regional {regional}")

@app.route('/passagens_regionais/<regional>/<turno>')
@login_required
def passagens_regionais_turno(regional, turno):
    # Parâmetros de paginação
    pagina = request.args.get('pagina', 1, type=int)
    itens_por_pagina = request.args.get('itens_por_pagina', 10, type=int)
    
    passagens = carregar_passagens_ordenadas()  # Já ordenadas por ID DESC
    passagens_filtradas = [p for p in passagens if p.get('regional') == regional and p.get('turno') == turno]
    
    # Aplica paginação
    dados_paginados = paginar_dados(passagens_filtradas, pagina, itens_por_pagina)
    
    return render_template('passagens.html', 
                         passagens=dados_paginados['itens'],
                         pagina_atual=dados_paginados['pagina_atual'],
                         total_paginas=dados_paginados['total_paginas'],
                         total_passagens=dados_paginados['total_itens'],
                         itens_por_pagina=dados_paginados['itens_por_pagina'],
                         titulo=f"Passagens - Regional {regional} - Turno {turno}")

@app.route('/passagens_turno/<turno>')
@login_required
def passagens_por_turno(turno):
    # Parâmetros de paginação
    pagina = request.args.get('pagina', 1, type=int)
    itens_por_pagina = request.args.get('itens_por_pagina', 10, type=int)
    
    passagens = carregar_passagens_ordenadas()  # Já ordenadas por ID DESC
    passagens_filtradas = [p for p in passagens if p.get('turno') == turno]
    
    # Aplica paginação
    dados_paginados = paginar_dados(passagens_filtradas, pagina, itens_por_pagina)
    
    return render_template('passagens.html', 
                         passagens=dados_paginados['itens'],
                         pagina_atual=dados_paginados['pagina_atual'],
                         total_paginas=dados_paginados['total_paginas'],
                         total_passagens=dados_paginados['total_itens'],
                         itens_por_pagina=dados_paginados['itens_por_pagina'],
                         titulo=f"Passagens - Turno {turno}")

@app.route('/passagens_filtro_data', methods=['GET', 'POST'])
@login_required
def passagens_filtro_data():
    # Parâmetros de paginação
    pagina = request.args.get('pagina', 1, type=int)
    itens_por_pagina = request.args.get('itens_por_pagina', 10, type=int)
    
    data_inicio = request.form.get('data_inicio') or request.args.get('data_inicio')
    data_fim = request.form.get('data_fim') or request.args.get('data_fim')
    
    if request.method == 'POST' or (data_inicio and data_fim):
        if data_inicio and data_fim:
            # Converte as datas para o formato de comparação
            try:
                data_inicio_obj = datetime.datetime.strptime(data_inicio, '%Y-%m-%d')
                data_fim_obj = datetime.datetime.strptime(data_fim, '%Y-%m-%d')
                
                passagens = carregar_passagens()
                passagens_filtradas = []
                
                for passagem in passagens:
                    try:
                        data_plantao_obj = parse_data_para_ordenacao(passagem['data_plantao'])
                        if data_inicio_obj <= data_plantao_obj <= data_fim_obj:
                            passagens_filtradas.append(passagem)
                    except:
                        continue
                
                # CORREÇÃO: Ordena por ID DESC (mais recente primeiro)
                passagens_filtradas.sort(key=lambda x: x.get('id', 0), reverse=True)
                
                # Aplica paginação
                dados_paginados = paginar_dados(passagens_filtradas, pagina, itens_por_pagina)
                
                return render_template('passagens_filtro_data.html', 
                                     passagens=dados_paginados['itens'],
                                     pagina_atual=dados_paginados['pagina_atual'],
                                     total_paginas=dados_paginados['total_paginas'],
                                     total_passagens=dados_paginados['total_itens'],
                                     itens_por_pagina=dados_paginados['itens_por_pagina'],
                                     titulo=f"Passagens - Período {converter_data_iso_para_br(data_inicio)} a {converter_data_iso_para_br(data_fim)}",
                                     data_inicio=data_inicio,
                                     data_fim=data_fim)
            
            except ValueError as e:
                flash('Datas inválidas!', 'error')
                print(f"Erro ao processar datas: {e}")
    
    # Se for GET ou se não houver filtro, mostra todas ORDENADAS por ID DESC
    passagens_ordenadas = carregar_passagens_ordenadas()  # Já ordenadas por ID DESC
    
    # Aplica paginação
    dados_paginados = paginar_dados(passagens_ordenadas, pagina, itens_por_pagina)
    
    return render_template('passagens_filtro_data.html', 
                         passagens=dados_paginados['itens'],
                         pagina_atual=dados_paginados['pagina_atual'],
                         total_paginas=dados_paginados['total_paginas'],
                         total_passagens=dados_paginados['total_itens'],
                         itens_por_pagina=dados_paginados['itens_por_pagina'],
                         titulo="Todas as Passagens")

@app.route('/meus_rascunhos')
@login_required
def meus_rascunhos():
    """Mostra os rascunhos do usuário atual"""
    # Parâmetros de paginação
    pagina = request.args.get('pagina', 1, type=int)
    itens_por_pagina = request.args.get('itens_por_pagina', 10, type=int)
    
    # Carrega todas as passagens
    passagens_todas = carregar_passagens()
    
    # Filtra apenas os rascunhos do usuário atual
    usuario_atual = session['usuario']
    rascunhos = [
        p for p in passagens_todas 
        if p.get('usuario') == usuario_atual and p.get('rascunho', False)
    ]
    
    # Ordena por data de registro (mais recente primeiro)
    rascunhos.sort(key=lambda x: x.get('id', 0), reverse=True)
    
    # Aplica paginação
    dados_paginados = paginar_dados(rascunhos, pagina, itens_por_pagina)
    
    return render_template('meus_rascunhos.html', 
                         rascunhos=dados_paginados['itens'],
                         pagina_atual=dados_paginados['pagina_atual'],
                         total_paginas=dados_paginados['total_paginas'],
                         total_rascunhos=dados_paginados['total_itens'],
                         itens_por_pagina=dados_paginados['itens_por_pagina'])

@app.route('/passagem/editar/<int:passagem_id>', methods=['GET', 'POST'])
@login_required
def editar_passagem(passagem_id):
    passagens = carregar_passagens()
    passagem = next((p for p in passagens if p['id'] == passagem_id), None)
    
    if not passagem:
        flash('Passagem não encontrada!', 'error')
        return redirect(url_for('meus_rascunhos'))
    
    # Verifica se o usuário é o dono do rascunho
    if passagem['usuario'] != session['usuario']:
        flash('Você não tem permissão para editar esta passagem!', 'error')
        return redirect(url_for('meus_rascunhos'))
    
    usuarios = carregar_usuarios()
    
    if request.method == 'POST':
        # Atualiza os dados da passagem
        salvar_como_rascunho = request.form.get('salvar_como_rascunho') == 'true'
        
        passagem['data_plantao_iso'] = request.form['data_plantao']
        passagem['data_plantao'] = converter_data_iso_para_br(request.form['data_plantao'])
        passagem['turno'] = request.form['turno']
        passagem['regional'] = request.form['regional']
        passagem['informacoes'] = request.form['informacoes']
        passagem['operadores_notificados'] = request.form.getlist('operadores')
        
        # Atualiza os outros campos...
        passagem['manutencao_acionada'] = request.form.get('manutencao_acionada') == 'sim'
        passagem['componente_manutencao'] = request.form.getlist('componente_manutencao[]')
        # ... atualize todos os outros campos similares
        
        passagem['data_registro'] = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
        
        if salvar_como_rascunho:
            passagem['rascunho'] = True
            flash('Rascunho atualizado com sucesso!', 'success')
            salvar_passagens(passagens)
            return redirect(url_for('meus_rascunhos'))
        else:
            passagem['rascunho'] = False
            salvar_passagens(passagens)
            
            # Envia notificações
            passagem_info = {
                'regional': passagem['regional'],
                'turno': passagem['turno'],
                'data_plantao': passagem['data_plantao'],
                'registrado_por': session['nome_completo'],
                'informacoes': passagem['informacoes']
            }
            
            if passagem['operadores_notificados']:
                titulo_notificacao = f"Passagem de Turno - {passagem['regional']} - {passagem['turno']}"
                adicionar_notificacao(passagem['operadores_notificados'], passagem['id'], titulo_notificacao, session['nome_completo'])
                enviar_whatsapp_notificacao(passagem['operadores_notificados'], passagem_info)
                
                flash(f'Passagem enviada e {len(passagem["operadores_notificados"])} operador(es) notificado(s)!', 'success')
            else:
                flash('Passagem enviada com sucesso!', 'success')
            
            return redirect(url_for('listar_passagens'))
    
    # Filtra apenas usuários que não são admin para notificação
    operadores = {user: info for user, info in usuarios.items() 
                 if info['nivel'] == 'usuario' and user != session['usuario']}
    
    return render_template('editar_passagem.html', passagem=passagem, operadores=operadores)

@app.route('/passagem/atualizar/<int:passagem_id>', methods=['POST'])
@login_required
def atualizar_passagem(passagem_id):
    """Atualiza uma passagem existente - VERSÃO CORRIGIDA"""
    passagens = carregar_passagens()
    passagem = next((p for p in passagens if p['id'] == passagem_id), None)
    
    if not passagem:
        flash('Passagem não encontrada!', 'error')
        return redirect(url_for('meus_rascunhos'))
    
    # Verifica se o usuário é o dono
    if passagem['usuario'] != session['usuario']:
        flash('Você não tem permissão para editar esta passagem!', 'error')
        return redirect(url_for('meus_rascunhos'))
    
    # DEBUG: Mostrar todos os dados recebidos
    print("🔍 DEBUG - Dados recebidos no formulário:")
    for key in request.form.keys():
        values = request.form.getlist(key)
        print(f"  {key}: {values}")
    
    # Processa os dados do formulário
    salvar_como_rascunho = request.form.get('salvar_como_rascunho') == 'true'
    
    # Atualiza TODOS os campos - CORRIGIDO PARA CAMPOS DINÂMICOS
    passagem['data_plantao_iso'] = request.form['data_plantao']
    passagem['data_plantao'] = converter_data_iso_para_br(request.form['data_plantao'])
    passagem['turno'] = request.form['turno']
    passagem['regional'] = request.form['regional']
    passagem['informacoes'] = request.form['informacoes']
    passagem['operadores_notificados'] = request.form.getlist('operadores')
    
    # CAMPOS DE MANUTENÇÃO - CORRIGIDO
    passagem['manutencao_acionada'] = request.form.get('manutencao_acionada') == 'sim'
    passagem['componente_manutencao'] = request.form.getlist('componente_manutencao[]')
    passagem['numero_ss'] = request.form.getlist('numero_ss[]')
    passagem['tecnico_acionado'] = request.form.getlist('tecnico_acionado[]')
    passagem['numero_oc'] = request.form.getlist('numero_oc[]')
    
    # CAMPOS DE EQUIPE - CORRIGIDO
    passagem['equipe_nao_apresentou'] = request.form.get('equipe_nao_apresentou') == 'sim'
    passagem['equipe_ausente'] = request.form.getlist('equipe_ausente[]')
    passagem['motivo_ausencia'] = request.form.getlist('motivo_ausencia[]')
    
    # CAMPOS DE ÁREA FORA - CORRIGIDO
    passagem['area_fora'] = request.form.get('area_fora') == 'sim'
    passagem['componente_area_fora'] = request.form.getlist('componente_area_fora[]')
    passagem['numero_componente_area_fora'] = request.form.getlist('numero_componente_area_fora[]')
    passagem['equipes_acionadas'] = request.form.getlist('equipes_acionadas[]')
    
    # CAMPOS DE LINHA VIVA
    passagem['linha_viva_acionada'] = request.form.get('linha_viva_acionada') == 'sim'
    passagem['detalhes_linha_viva'] = request.form.get('detalhes_linha_viva', '')
    
    # CAMPOS DE ORDENS DE SERVIÇO - CORRIGIDO
    passagem['os_priorizar'] = request.form.getlist('os_priorizar[]')
    passagem['oc_18h'] = request.form.getlist('oc_18h[]')
    passagem['oc_24h'] = request.form.getlist('oc_24h[]')
    
    # CAMPOS DE TRANSFERÊNCIA DE CARGA
    passagem['transferencia_carga'] = request.form.get('transferencia_carga') == 'sim'
    passagem['alimentadores_envolvidos'] = request.form.get('alimentadores_envolvidos', '')
    
    passagem['data_registro'] = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    
    # DEBUG: Mostrar dados que serão salvos
    print("💾 DEBUG - Dados que serão salvos:")
    print(f"  Manutenção: {passagem['manutencao_acionada']}")
    print(f"  Componentes Manutenção: {passagem['componente_manutencao']}")
    print(f"  Números SS: {passagem['numero_ss']}")
    print(f"  Técnicos: {passagem['tecnico_acionado']}")
    print(f"  Equipes Ausentes: {passagem['equipe_ausente']}")
    print(f"  Áreas Fora: {passagem['componente_area_fora']}")
    print(f"  OS Priorizar: {passagem['os_priorizar']}")
    
    if salvar_como_rascunho:
        passagem['rascunho'] = True
        flash('Rascunho atualizado com sucesso!', 'success')
        salvar_passagens(passagens)
        return redirect(url_for('meus_rascunhos'))
    else:
        passagem['rascunho'] = False
        salvar_passagens(passagens)
        
        # Envia notificações
        passagem_info = {
            'regional': passagem['regional'],
            'turno': passagem['turno'],
            'data_plantao': passagem['data_plantao'],
            'registrado_por': session['nome_completo'],
            'informacoes': passagem['informacoes']
        }
        
        if passagem['operadores_notificados']:
            titulo_notificacao = f"Passagem de Turno - {passagem['regional']} - {passagem['turno']}"
            adicionar_notificacao(passagem['operadores_notificados'], passagem['id'], titulo_notificacao, session['nome_completo'])
            enviar_whatsapp_notificacao(passagem['operadores_notificados'], passagem_info)
            
            flash(f'Passagem atualizada e {len(passagem["operadores_notificados"])} operador(es) notificado(s)!', 'success')
        else:
            flash('Passagem atualizada com sucesso!', 'success')
        
        return redirect(url_for('listar_passagens'))
    
@app.route('/passagem/excluir/<int:passagem_id>')
@login_required
def excluir_passagem(passagem_id):
    passagens = carregar_passagens()
    passagem = next((p for p in passagens if p['id'] == passagem_id), None)
    
    if not passagem:
        flash('Passagem não encontrada!', 'error')
        return redirect(url_for('meus_rascunhos'))
    
    # Verifica se o usuário é o dono do rascunho
    if passagem['usuario'] != session['usuario'] or not passagem.get('rascunho', False):
        flash('Você não tem permissão para excluir esta passagem!', 'error')
        return redirect(url_for('meus_rascunhos'))
    
    passagens.remove(passagem)
    salvar_passagens(passagens)
    flash('Rascunho excluído com sucesso!', 'success')
    return redirect(url_for('meus_rascunhos'))
    
@app.route('/passagem/nova', methods=['GET', 'POST'])
@login_required
def nova_passagem():
    usuarios = carregar_usuarios()
    
    if request.method == 'POST':
        # Verifica se é para salvar como rascunho ou enviar
        salvar_como_rascunho = request.form.get('salvar_como_rascunho') == 'true'
        
        data_plantao_iso = request.form['data_plantao']
        data_plantao_br = converter_data_iso_para_br(data_plantao_iso)
        turno = request.form['turno']
        regional = request.form['regional']
        informacoes = request.form['informacoes']
        operadores_selecionados = request.form.getlist('operadores')
        
        # NOVOS CAMPOS - Processar como arrays
        manutencao_acionada = request.form.get('manutencao_acionada') == 'sim'
        componente_manutencao = request.form.getlist('componente_manutencao[]')
        numero_ss = request.form.getlist('numero_ss[]')
        tecnico_acionado = request.form.getlist('tecnico_acionado[]')
        numero_oc = request.form.getlist('numero_oc[]')
        
        equipe_nao_apresentou = request.form.get('equipe_nao_apresentou') == 'sim'
        equipe_ausente = request.form.getlist('equipe_ausente[]')
        motivo_ausencia = request.form.getlist('motivo_ausencia[]')
        
        area_fora = request.form.get('area_fora') == 'sim'
        componente_area_fora = request.form.getlist('componente_area_fora[]')
        numero_componente_area_fora = request.form.getlist('numero_componente_area_fora[]')
        equipes_acionadas = request.form.getlist('equipes_acionadas[]')
        
        linha_viva_acionada = request.form.get('linha_viva_acionada') == 'sim'
        detalhes_linha_viva = request.form.get('detalhes_linha_viva', '')
        
        os_priorizar = request.form.getlist('os_priorizar[]')
        oc_18h = request.form.getlist('oc_18h[]')
        oc_24h = request.form.getlist('oc_24h[]')
        
        transferencia_carga = request.form.get('transferencia_carga') == 'sim'
        alimentadores_envolvidos = request.form.get('alimentadores_envolvidos', '')
        
        passagens = carregar_passagens()
        
        nova_passagem = {
            'id': len(passagens) + 1,
            'usuario': session['usuario'],
            'nome_completo': session['nome_completo'],
            'data_registro': datetime.datetime.now().strftime('%d/%m/%Y %H:%M'),
            'data_plantao': data_plantao_br,
            'turno': turno,
            'regional': regional,
            'informacoes': informacoes,
            'operadores_notificados': operadores_selecionados,
            
            # NOVOS CAMPOS - Arrays
            'manutencao_acionada': manutencao_acionada,
            'componente_manutencao': componente_manutencao,
            'numero_ss': numero_ss,
            'tecnico_acionado': tecnico_acionado,
            'numero_oc': numero_oc,
            
            'equipe_nao_apresentou': equipe_nao_apresentou,
            'equipe_ausente': equipe_ausente,
            'motivo_ausencia': motivo_ausencia,
            
            'area_fora': area_fora,
            'componente_area_fora': componente_area_fora,
            'numero_componente_area_fora': numero_componente_area_fora,
            'equipes_acionadas': equipes_acionadas,
            
            'linha_viva_acionada': linha_viva_acionada,
            'detalhes_linha_viva': detalhes_linha_viva,
            
            'os_priorizar': os_priorizar,
            'oc_18h': oc_18h,
            'oc_24h': oc_24h,
            
            'transferencia_carga': transferencia_carga,
            'alimentadores_envolvidos': alimentadores_envolvidos,
            
            # Campo para identificar rascunho
            'rascunho': salvar_como_rascunho
        }
        
        passagens.append(nova_passagem)
        salvar_passagens(passagens)
        
        if salvar_como_rascunho:
            flash('Rascunho salvo com sucesso! Você pode editá-lo depois.', 'success')
            return redirect(url_for('meus_rascunhos'))
        else:
            # Informações para notificação
            passagem_info = {
                'regional': regional,
                'turno': turno,
                'data_plantao': data_plantao_br,
                'registrado_por': session['nome_completo'],
                'informacoes': informacoes
            }
            
            # Adiciona informações específicas para o WhatsApp
            mensagem_adicional = ""
            
            if manutencao_acionada:
                mensagem_adicional += f"\n🔧 *Manutenção Acionada:* {componente_manutencao}"
                if numero_ss:
                    mensagem_adicional += f"\n📋 *SS:* {numero_ss}"
                if tecnico_acionado:
                    mensagem_adicional += f"\n👨‍🔧 *Técnico:* {tecnico_acionado}"
            
            if equipe_nao_apresentou:
                mensagem_adicional += f"\n⚠️ *Equipe Ausente:* {equipe_ausente} - {motivo_ausencia}"
            
            if linha_viva_acionada:
                mensagem_adicional += f"\n⚡ *Linha Viva Acionada:* {detalhes_linha_viva}"
            
            if os_priorizar:
                mensagem_adicional += f"\n🎯 *OS Prioritária:* {os_priorizar}"
            
            if oc_18h:
                mensagem_adicional += f"\n⏰ *OS 18h:* {oc_18h}"
            
            if oc_24h:
                mensagem_adicional += f"\n🕐 *OS 24h:* {oc_24h}"
            
            if transferencia_carga:
                mensagem_adicional += f"\n🔄 *Transferência de Carga:* {alimentadores_envolvidos}"
            
            passagem_info['informacoes'] += mensagem_adicional
            
            # Adiciona notificações para os operadores selecionados
            if operadores_selecionados:
                titulo_notificacao = f"Passagem de Turno - {regional} - {turno}"
                adicionar_notificacao(operadores_selecionados, nova_passagem['id'], titulo_notificacao, session['nome_completo'])
                
                # ENVIA WHATSAPP
                enviar_whatsapp_notificacao(operadores_selecionados, passagem_info)
                
                flash(f'Passagem registrada e {len(operadores_selecionados)} operador(es) notificado(s)!', 'success')
            else:
                flash('Passagem de turno registrada com sucesso!', 'success')
            
            return redirect(url_for('listar_passagens'))
    
    # Filtra apenas usuários que não são admin para notificação
    operadores = {user: info for user, info in usuarios.items() 
                 if info['nivel'] == 'usuario' and user != session['usuario']}
    
    return render_template('nova_passagem.html', operadores=operadores)

@app.route('/usuarios')
@admin_required
def listar_usuarios():
    usuarios = carregar_usuarios()
    return render_template('usuarios.html', 
                         usuarios=usuarios)

@app.route('/usuario/novo', methods=['GET', 'POST'])
@admin_required
def novo_usuario():
    if request.method == 'POST':
        novo_usuario = request.form['usuario'].lower()
        senha = request.form['senha']
        confirmar_senha = request.form['confirmar_senha']
        nivel = request.form['nivel']
        nome_completo = request.form['nome_completo']
        
        # NOVOS CAMPOS
        email = request.form.get('email', '').strip()
        telefone = request.form.get('telefone', '').strip()
        whatsapp = request.form.get('whatsapp', '').strip()
        
        usuarios = carregar_usuarios()
        
        if novo_usuario in usuarios:
            flash('Usuário já existe!', 'error')
            return redirect(url_for('novo_usuario'))
        
        if senha != confirmar_senha:
            flash('Senhas não coincidem!', 'error')
            return redirect(url_for('novo_usuario'))
        
        # Cria usuário com todos os campos
        usuarios[novo_usuario] = {
            'senha': senha,
            'nivel': nivel,
            'nome_completo': nome_completo,
            'email': email if email else f"{novo_usuario}@empresa.com",
            'telefone': telefone,
            'whatsapp': whatsapp
        }
        
        salvar_usuarios(usuarios)
        flash('Usuário cadastrado com sucesso!', 'success')
        return redirect(url_for('listar_usuarios'))
    
    return render_template('novo_usuario.html')

@app.route('/usuario/excluir/<username>')
@admin_required
def excluir_usuario(username):
    if username == 'admin':
        flash('Não é possível excluir o usuário admin!', 'error')
        return redirect(url_for('listar_usuarios'))
    
    usuarios = carregar_usuarios()
    if username in usuarios:
        nome_completo = usuarios[username]['nome_completo']
        del usuarios[username]
        salvar_usuarios(usuarios)
        flash(f'Usuário {nome_completo} ({username}) excluído com sucesso!', 'success')
    else:
        flash('Usuário não encontrado!', 'error')
    
    return redirect(url_for('listar_usuarios'))

@app.route('/buscar')
@login_required
def buscar_passagens():
    termo = request.args.get('q', '').lower()
    
    # Parâmetros de paginação
    pagina = request.args.get('pagina', 1, type=int)
    itens_por_pagina = request.args.get('itens_por_pagina', 10, type=int)
    
    passagens = carregar_passagens_ordenadas()  # Já ordenadas por ID DESC
    
    if termo:
        resultados = []
        for passagem in passagens:
            if (termo in passagem.get('usuario', '').lower() or 
                termo in passagem.get('nome_completo', '').lower() or
                termo in passagem.get('data_plantao', '').lower() or 
                termo in passagem.get('turno', '').lower() or 
                termo in passagem.get('regional', '').lower() or
                termo in passagem.get('informacoes', '').lower()):
                resultados.append(passagem)
        passagens = resultados
    
    # Aplica paginação
    dados_paginados = paginar_dados(passagens, pagina, itens_por_pagina)
    
    return render_template('buscar.html', 
                         passagens=dados_paginados['itens'], 
                         termo_busca=termo,
                         pagina_atual=dados_paginados['pagina_atual'],
                         total_paginas=dados_paginados['total_paginas'],
                         total_passagens=dados_paginados['total_itens'],
                         itens_por_pagina=dados_paginados['itens_por_pagina'])

@app.route('/notificacoes')
@login_required
def listar_notificacoes():
    filtro = request.args.get('filtro', '')
    notificacoes = carregar_notificacoes()
    minhas_notificacoes = notificacoes.get(session['usuario'], [])
    
    # Ordena por data (mais recente primeiro)
    minhas_notificacoes.sort(key=lambda x: datetime.datetime.strptime(x['data'], '%d/%m/%Y %H:%M'), reverse=True)
    
    # Aplica filtro se especificado
    if filtro == 'nao_lidas':
        minhas_notificacoes = [n for n in minhas_notificacoes if not n['lida']]
    elif filtro == 'lidas':
        minhas_notificacoes = [n for n in minhas_notificacoes if n['lida']]
    
    # Calcula estatísticas para os cartões
    total_notificacoes = len(minhas_notificacoes)
    nao_lidas = sum(1 for n in minhas_notificacoes if not n['lida'])
    lidas = total_notificacoes - nao_lidas
    
    # Notificações dos últimos 7 dias
    sete_dias_atras = datetime.datetime.now() - datetime.timedelta(days=7)
    recentes = sum(1 for n in minhas_notificacoes 
                  if datetime.datetime.strptime(n['data'], '%d/%m/%Y %H:%M') >= sete_dias_atras)
    
    return render_template('notificacoes.html', 
                         notificacoes=minhas_notificacoes,
                         notificacoes_recentes=recentes)

@app.route('/minhas_passagens_notificadas')
@login_required
def minhas_passagens_notificadas():
    """Mostra apenas as passagens que notificaram o usuário atual"""
    # Parâmetros de paginação
    pagina = request.args.get('pagina', 1, type=int)
    itens_por_pagina = request.args.get('itens_por_pagina', 10, type=int)
    
    # Carrega todas as passagens ordenadas
    passagens_todas = carregar_passagens_ordenadas()
    
    # Filtra apenas as passagens que notificaram o usuário atual
    usuario_atual = session['usuario']
    passagens_filtradas = [
        p for p in passagens_todas 
        if 'operadores_notificados' in p and usuario_atual in p['operadores_notificados']
    ]
    
    print(f"🔔 Passagens notificadas para {usuario_atual}: {len(passagens_filtradas)}")
    
    # Aplica paginação
    dados_paginados = paginar_dados(passagens_filtradas, pagina, itens_por_pagina)
    
    return render_template('minhas_passagens_notificadas.html', 
                         passagens=dados_paginados['itens'],
                         pagina_atual=dados_paginados['pagina_atual'],
                         total_paginas=dados_paginados['total_paginas'],
                         total_passagens=dados_paginados['total_itens'],
                         itens_por_pagina=dados_paginados['itens_por_pagina'],
                         titulo="Minhas Passagens Notificadas")

@app.route('/notificacao/marcar_lida/<int:notificacao_id>')
@login_required
def marcar_notificacao_lida(notificacao_id):
    notificacoes = carregar_notificacoes()
    usuario = session['usuario']
    
    if usuario in notificacoes:
        for notificacao in notificacoes[usuario]:
            if notificacao['id'] == notificacao_id:
                notificacao['lida'] = True
                break
        
        salvar_notificacoes(notificacoes)
        flash('Notificação marcada como lida!', 'success')
    
    return redirect(url_for('listar_notificacoes'))

@app.route('/notificacao/limpar_todas')
@login_required
def limpar_notificacoes():
    notificacoes = carregar_notificacoes()
    usuario = session['usuario']
    
    if usuario in notificacoes:
        notificacoes[usuario] = []
        salvar_notificacoes(notificacoes)
        flash('Todas as notificações foram limpas!', 'success')
    
    return redirect(url_for('listar_notificacoes'))
@app.route('/notificacao/detalhes_passagem/<int:notificacao_id>')
def detalhes_passagem_notificacao(notificacao_id):
    try:
        notificacao = Notificacao.query.get_or_404(notificacao_id)
        
        # Buscar a passagem associada à notificação
        passagem = PassagemTurno.query.filter_by(id=notificacao.passagem_id).first()
        
        if not passagem:
            return jsonify({'success': False, 'error': 'Passagem não encontrada'})
        
        # Usar o mesmo formato que a listagem de passagens
        # Se você tem um método específico para formatar passagens, use-o aqui
        passagem_data = {
            'id': passagem.id,
            'regional': passagem.regional,
            'turno': passagem.turno,
            'data_registro': passagem.data_registro,
            'data_plantao': passagem.data_plantao,
            'nome_completo': passagem.nome_completo,
            'informacoes': passagem.informacoes,
            
            # Campos booleanos - garantir que sejam booleanos
            'manutencao_acionada': bool(passagem.manutencao_acionada),
            'equipe_nao_apresentou': bool(passagem.equipe_nao_apresentou),
            'area_fora': bool(passagem.area_fora),
            'linha_viva_acionada': bool(passagem.linha_viva_acionada),
            'transferencia_carga': bool(passagem.transferencia_carga),
            
            # Campos de texto
            'componente_manutencao': passagem.componente_manutencao or '',
            'numero_ss': passagem.numero_ss or '',
            'tecnico_acionado': passagem.tecnico_acionado or '',
            'numero_oc': passagem.numero_oc or '',
            'equipe_ausente': passagem.equipe_ausente or '',
            'motivo_ausencia': passagem.motivo_ausencia or '',
            'componente_area_fora': passagem.componente_area_fora or '',
            'numero_componente_area_fora': passagem.numero_componente_area_fora or '',
            'equipes_acionadas': passagem.equipes_acionadas or '',
            'detalhes_linha_viva': passagem.detalhes_linha_viva or '',
            'os_priorizar': passagem.os_priorizar or '',
            'oc_18h': passagem.oc_18h or '',
            'oc_24h': passagem.oc_24h or '',
            'alimentadores_envolvidos': passagem.alimentadores_envolvidos or '',
            'operadores_notificados': passagem.operadores_notificados or []
        }
        
        html = render_template('_passagem_item.html', passagem=passagem_data)
        return jsonify({'success': True, 'html': html})
        
    except Exception as e:
        print(f"Erro ao carregar detalhes da passagem: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/teste_paginacao')
def teste_paginacao():
    """Rota de teste para paginação"""
    print("🎯 TESTE PAGINAÇÃO INICIADO!")
    
    passagens_todas = carregar_passagens_ordenadas()
    print(f"Total de passagens: {len(passagens_todas)}")
    
    # Teste com 5 itens por página (deve gerar 3 páginas com 11 passagens)
    print("\n🔍 TESTE COM 5 ITENS POR PÁGINA:")
    dados1 = paginar_dados(passagens_todas, pagina=1, itens_por_pagina=5)
    print(f"Página 1: {len(dados1['itens'])} itens")
    print(f"IDs na página 1: {[p['id'] for p in dados1['itens']]}")
    
    dados2 = paginar_dados(passagens_todas, pagina=2, itens_por_pagina=5)
    print(f"Página 2: {len(dados2['itens'])} itens") 
    print(f"IDs na página 2: {[p['id'] for p in dados2['itens']]}")
    
    dados3 = paginar_dados(passagens_todas, pagina=3, itens_por_pagina=5)
    print(f"Página 3: {len(dados3['itens'])} itens")
    print(f"IDs na página 3: {[p['id'] for p in dados3['itens']]}")
    
    print(f"\n📊 RESUMO: {dados1['total_paginas']} páginas no total")
    
    return """
    <h1>Teste de Paginação Concluído!</h1>
    <p>Verifique o terminal para ver os resultados.</p>
    <p>Total de passagens: 11</p>
    <p>Com 5 itens por página deveria ter: 3 páginas</p>
    <p><a href="/passagens">Ir para Todas as Passagens</a></p>
    """

# Função para migrar passagens antigas (executa automaticamente)
def migrar_passagens_antigas():
    """Adiciona o campo nome_completo às passagens antigas"""
    passagens = carregar_passagens()
    usuarios = carregar_usuarios()
    
    atualizadas = False
    for passagem in passagens:
        if 'nome_completo' not in passagem:
            usuario = passagem.get('usuario')
            if usuario in usuarios:
                passagem['nome_completo'] = usuarios[usuario]['nome_completo']
                atualizadas = True
            else:
                passagem['nome_completo'] = usuario  # Fallback para o username
                atualizadas = True
    
    if atualizadas:
        salvar_passagens(passagens)
        print("Passagens antigas migradas com sucesso!")

# Executa a migração automaticamente ao iniciar o app
@app.route('/teste')
def teste_simples():
    return "<h1>Teste OK! Servidor está funcionando.</h1>"
# Executa a migração automaticamente ao iniciar o app
@app.route('/notificacao/marcar_todas_lidas')
@login_required
def marcar_todas_lidas():
    """Marca todas as notificações do usuário como lidas"""
    try:
        notificacoes = carregar_notificacoes()
        usuario = session['usuario']
        
        if usuario in notificacoes:
            for notificacao in notificacoes[usuario]:
                notificacao['lida'] = True
            
            salvar_notificacoes(notificacoes)
            flash('Todas as notificações foram marcadas como lidas!', 'success')
        else:
            flash('Nenhuma notificação para marcar como lida.', 'info')
            
    except Exception as e:
        flash('Erro ao marcar notificações como lidas', 'danger')
        print(f"Erro em marcar_todas_lidas: {e}")
    
    return redirect(url_for('listar_notificacoes'))

@app.route('/notificacao/excluir/<int:notificacao_id>')
@login_required
def excluir_notificacao(notificacao_id):
    """Exclui uma notificação específica"""
    try:
        notificacoes = carregar_notificacoes()
        usuario = session['usuario']
        
        if usuario in notificacoes:
            # Filtra a notificação a ser removida
            notificacoes[usuario] = [n for n in notificacoes[usuario] if n['id'] != notificacao_id]
            
            salvar_notificacoes(notificacoes)
            flash('Notificação excluída com sucesso!', 'success')
        else:
            flash('Notificação não encontrada.', 'error')
            
    except Exception as e:
        flash('Erro ao excluir notificação', 'danger')
        print(f"Erro em excluir_notificacao: {e}")
    
    return redirect(url_for('listar_notificacoes'))

@app.route('/notificacao/limpar_lidas')
@login_required
def limpar_notificacoes_lidas():
    """Remove apenas as notificações já lidas"""
    try:
        notificacoes = carregar_notificacoes()
        usuario = session['usuario']
        
        if usuario in notificacoes:
            # Mantém apenas as notificações não lidas
            notificacoes_nao_lidas = [n for n in notificacoes[usuario] if not n['lida']]
            notificacoes[usuario] = notificacoes_nao_lidas
            
            salvar_notificacoes(notificacoes)
            flash('Notificações lidas removidas com sucesso!', 'success')
        else:
            flash('Nenhuma notificação lida para remover.', 'info')
            
    except Exception as e:
        flash('Erro ao limpar notificações lidas', 'danger')
        print(f"Erro em limpar_notificacoes_lidas: {e}")
    
    return redirect(url_for('listar_notificacoes'))

if __name__ == '__main__':
    migrar_passagens_antigas()
    
    # Mude para localhost apenas
    print("=" * 60)
    print("SISTEMA DE PASSAGENS DE TURNO - MODO DEBUG")
    print("=" * 60)
    print("Servidor iniciando...")
    print("Acesse: http://localhost:5000")
    print("=" * 60)
    print("Pressione Ctrl+C para parar o servidor")
    print("=" * 60)
    
    app.run(host='127.0.0.1', port=5000, debug=True)