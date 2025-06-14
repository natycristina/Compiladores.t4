import sys
from antlr4 import *
from LAParser import LAParser
from antlr4.error.ErrorListener import ErrorListener
from LALexer import LALexer
from LAListener import LAListener

# --- Definições de Tipos e Símbolos ---

class Simbolo:
    def __init__(self, nome, tipo, categoria, params=None, tipo_retorno=None):
        self.nome = nome
        self.tipo = tipo # Pode ser um TipoLA (para tipos mais complexos) ou string simples
        self.categoria = categoria # 'variavel', 'constante', 'procedimento', 'funcao', 'tipo'
        self.params = params if params is not None else [] # Para funções/procedimentos: lista de (nome_param, tipo_param, eh_var)
        self.tipo_retorno = tipo_retorno # Para funções

    def __repr__(self):
        if self.categoria in ['procedimento', 'funcao']:
            return f"Simbolo(Nome='{self.nome}', Categoria='{self.categoria}', Tipo='{self.tipo}', Params={self.params}, Retorno='{self.tipo_retorno}')"
        return f"Simbolo(Nome='{self.nome}', Categoria='{self.categoria}', Tipo='{self.tipo}')"

class TabelaDeSimbolos:
    def __init__(self):
        self.simbolos = {} # Dicionário: nome -> Simbolo

    def adicionar(self, simbolo_obj):
        if simbolo_obj.nome in self.simbolos:
            return False # Já existe no escopo atual
        self.simbolos[simbolo_obj.nome] = simbolo_obj
        return True

    def buscar(self, nome):
        return self.simbolos.get(nome)

# Definindo tipos mais complexos para ponteiros e registros
class TipoLA:
    def __init__(self, nome_base, is_ponteiro=False, campos=None):
        self.nome_base = nome_base # 'literal', 'inteiro', 'real', 'logico', nome de registro
        self.is_ponteiro = is_ponteiro
        self.campos = campos # Para registros: dicionário {nome_campo: tipo_campo}

    def __eq__(self, other):
        if not isinstance(other, TipoLA):
            return False
        return (self.nome_base == other.nome_base and
                self.is_ponteiro == other.is_ponteiro and
                self.campos == other.campos)

    def __str__(self):
        prefixo_ponteiro = "^" if self.is_ponteiro else ""
        if self.campos:
            return f"{prefixo_ponteiro}registro {self.nome_base}"
        return f"{prefixo_ponteiro}{self.nome_base}"

    def __repr__(self):
        return self.__str__()

# Lista de tipos primitivos (não ponteiros e não registros)
TIPOS_PRIMITIVOS = {'literal', 'inteiro', 'real', 'logico'}

# --- Classe do Analisador Semântico ---

class AnalisadorSemantico(LAListener):
    def __init__(self, token_stream):
        self.pilha_tabelas = [TabelaDeSimbolos()] # Pilha de tabelas de símbolos
        self.erros = []
        self.tokens = token_stream
        self.tipo_retorno_atual = None # Para verificar 'retorne' em funções

    # Métodos auxiliares para gerenciar escopo
    def empilhar_escopo(self):
        self.pilha_tabelas.append(TabelaDeSimbolos())

    def desempilhar_escopo(self):
        if len(self.pilha_tabelas) > 1: # Não desempilha o escopo global
            self.pilha_tabelas.pop()

    def buscar_simbolo(self, nome):
        # Busca do escopo mais interno para o mais externo
        for tabela in reversed(self.pilha_tabelas):
            simbolo = tabela.buscar(nome)
            if simbolo:
                return simbolo
        return None

    def adicionar_simbolo_escopo_atual(self, simbolo_obj, token):
        if not self.pilha_tabelas[-1].adicionar(simbolo_obj):
            # Erro: identificador já declarado no escopo atual
            self.erros.append(f"Linha {token.line}: identificador {simbolo_obj.nome} ja declarado anteriormente")
            return False
        return True

    def linha_token(self, token):
        return token.line

    # --- Análise de Tipos de Expressão (Refatorada) ---
    def tipo_expressao(self, ctx):
        if isinstance(ctx, LAParser.ExpressaoContext):
            return self.tipo_expressao(ctx.expressao_logica())

        elif isinstance(ctx, LAParser.Expressao_logicaContext):
            tipos = [self.tipo_expressao(child) for child in ctx.expressao_relacional()]

            if len(tipos) == 1:
                return tipos[0]

            # Operadores lógicos exigem 'logico'
            if all(t and t.nome_base == 'logico' and not t.is_ponteiro and not t.campos for t in tipos):
                return TipoLA('logico')
            else:
                return TipoLA('indefinido') # Erro de tipo na expressão lógica

        elif isinstance(ctx, LAParser.Expressao_relacionalContext):
            if ctx.getChildCount() == 1:
                return self.tipo_expressao(ctx.expressao_aritmetica(0))
            else:
                tipo_esq = self.tipo_expressao(ctx.expressao_aritmetica(0))
                tipo_dir = self.tipo_expressao(ctx.expressao_aritmetica(1))

                if not tipo_esq or not tipo_dir:
                    return TipoLA('indefinido')

                # Compatibilidade para relacionais (numéricos ou mesmo tipo)
                if ((tipo_esq.nome_base in {'inteiro', 'real'} and tipo_dir.nome_base in {'inteiro', 'real'}) or
                    (tipo_esq == tipo_dir)):
                    return TipoLA('logico')
                return TipoLA('indefinido')

        elif isinstance(ctx, LAParser.Expressao_aritmeticaContext):
            tipos = [self.tipo_expressao(term) for term in ctx.termo()]
            if not tipos:
                return TipoLA('indefinido')

            tipo_acumulado = tipos[0]
            if not tipo_acumulado:
                return TipoLA('indefinido')

            for t in tipos[1:]:
                if not t:
                    return TipoLA('indefinido')

                if (tipo_acumulado.nome_base in {'inteiro', 'real'} and not tipo_acumulado.is_ponteiro and not tipo_acumulado.campos and
                    t.nome_base in {'inteiro', 'real'} and not t.is_ponteiro and not t.campos):
                    tipo_acumulado = TipoLA('real') if 'real' in (tipo_acumulado.nome_base, t.nome_base) else TipoLA('inteiro')
                elif tipo_acumulado.nome_base == 'literal' and not tipo_acumulado.is_ponteiro and not tipo_acumulado.campos and \
                     t.nome_base == 'literal' and not t.is_ponteiro and not t.campos:
                    tipo_acumulado = TipoLA('literal') # Concatenação
                else:
                    self.erros.append(f"Linha {ctx.start.line}: incompatibilidade de tipos em operacao aritmetica entre {tipo_acumulado} e {t}")
                    return TipoLA('indefinido')
            return tipo_acumulado

        elif isinstance(ctx, LAParser.TermoContext):
            tipos = [self.tipo_expressao(fat) for fat in ctx.fator()]
            if not tipos:
                return TipoLA('indefinido')

            tipo_acumulado = tipos[0]
            if not tipo_acumulado:
                return TipoLA('indefinido')

            for t in tipos[1:]:
                if not t:
                    return TipoLA('indefinido')

                if (tipo_acumulado.nome_base in {'inteiro', 'real'} and not tipo_acumulado.is_ponteiro and not tipo_acumulado.campos and
                    t.nome_base in {'inteiro', 'real'} and not t.is_ponteiro and not t.campos):
                    tipo_acumulado = TipoLA('real') if 'real' in (tipo_acumulado.nome_base, t.nome_base) else TipoLA('inteiro')
                else:
                    self.erros.append(f"Linha {ctx.start.line}: incompatibilidade de tipos em operacao aritmetica entre {tipo_acumulado} e {t}")
                    return TipoLA('indefinido')
            return tipo_acumulado

        elif isinstance(ctx, LAParser.FatorContext):
            if ctx.NUM_INT():
                return TipoLA('inteiro')
            elif ctx.NUM_REAL():
                return TipoLA('real')
            elif ctx.CADEIA():
                return TipoLA('literal')
            elif ctx.getText() in ('verdadeiro', 'falso'):
                return TipoLA('logico')
            elif ctx.ABREPAR():
                return self.tipo_expressao(ctx.expressao())
            elif ctx.CIRCUNFLEXO() and ctx.IDENT(): # Ponteiro
                nome_ident = ctx.IDENT().getText()
                simbolo = self.buscar_simbolo(nome_ident)
                if not simbolo:
                    self.erros.append(f"Linha {ctx.IDENT().symbol.line}: identificador {nome_ident} nao declarado")
                    return TipoLA('indefinido')
                # Se o símbolo é um ponteiro, seu tipo 'desreferenciado' é o tipo base
                if simbolo.tipo.is_ponteiro:
                    return TipoLA(simbolo.tipo.nome_base)
                else:
                    self.erros.append(f"Linha {ctx.IDENT().symbol.line}: uso indevido de ponteiro com identificador {nome_ident}")
                    return TipoLA('indefinido')
            elif ctx.IDENT():
                nome = ctx.IDENT().getText()
                simbolo = self.buscar_simbolo(nome)
                if not simbolo:
                    self.erros.append(f"Linha {ctx.IDENT().symbol.line}: identificador {nome} nao declarado")
                    return TipoLA('indefinido')
                return simbolo.tipo # Retorna o objeto TipoLA do símbolo
            elif ctx.chamada_funcao():
                return self.tipo_chamada_funcao(ctx.chamada_funcao())
            elif ctx.acesso_campo():
                return self.tipo_acesso_campo(ctx.acesso_campo())
            elif ctx.subliteral():
                # subLiteral sempre retorna literal
                return TipoLA('literal')
            elif ctx.potencia():
                # Potencia retorna inteiro ou real dependendo dos operandos
                exp1_type = self.tipo_expressao(ctx.potencia().expressao(0))
                exp2_type = self.tipo_expressao(ctx.potencia().expressao(1))

                if (exp1_type and exp1_type.nome_base in {'inteiro', 'real'} and not exp1_type.is_ponteiro and not exp1_type.campos) and \
                   (exp2_type and exp2_type.nome_base in {'inteiro', 'real'} and not exp2_type.is_ponteiro and not exp2_type.campos):
                    if exp1_type.nome_base == 'real' or exp2_type.nome_base == 'real':
                        return TipoLA('real')
                    return TipoLA('inteiro')
                else:
                    self.erros.append(f"Linha {ctx.potencia().start.line}: operandos invalidos para potencia")
                    return TipoLA('indefinido')
            elif ctx.getChildCount() == 2 and ctx.getChild(0).getText() == '-': # Negação unária
                t = self.tipo_expressao(ctx.fator())
                if t and t.nome_base in {'inteiro', 'real'} and not t.is_ponteiro and not t.campos:
                    return t
                else:
                    self.erros.append(f"Linha {ctx.start.line}: operando invalido para negacao unaria")
                    return TipoLA('indefinido')
            elif ctx.getChildCount() == 2 and ctx.getChild(0).getText().lower() == 'nao': # Negação lógica
                t = self.tipo_expressao(ctx.fator())
                if t and t.nome_base == 'logico' and not t.is_ponteiro and not t.campos:
                    return TipoLA('logico')
                else:
                    self.erros.append(f"Linha {ctx.start.line}: operando invalido para negacao logica")
                    return TipoLA('indefinido')
            elif ctx.getChildCount() == 2 and ctx.getChild(0).getText() == '&': # Endereçamento
                # O tipo do endereçamento é um ponteiro para o tipo da variável/campo
                if ctx.IDENT():
                    nome_ident = ctx.IDENT().getText()
                    simbolo = self.buscar_simbolo(nome_ident)
                    if not simbolo:
                        self.erros.append(f"Linha {ctx.IDENT().symbol.line}: identificador {nome_ident} nao declarado")
                        return TipoLA('indefinido')
                    return TipoLA(simbolo.tipo.nome_base, is_ponteiro=True) # Ponteiro para o tipo base
                elif ctx.acesso_campo():
                    tipo_campo = self.tipo_acesso_campo(ctx.acesso_campo())
                    if tipo_campo and tipo_campo.nome_base != 'indefinido':
                        return TipoLA(tipo_campo.nome_base, is_ponteiro=True)
                    return TipoLA('indefinido')
                return TipoLA('indefinido')

        return TipoLA('indefinido') # Caso não reconhecido

    # --- Verificação de Compatibilidade de Atribuição ---
    def eh_compativel_atribuicao(self, tipo_var_obj, tipo_exp_obj):
        if not tipo_var_obj or not tipo_exp_obj:
            return False # Um dos tipos é indefinido

        # ponteiro <- endereco
        if tipo_var_obj.is_ponteiro and tipo_exp_obj.is_ponteiro:
            return tipo_var_obj.nome_base == tipo_exp_obj.nome_base
        
        # (real | inteiro) <- (real | inteiro)
        if tipo_var_obj.nome_base in {'real', 'inteiro'} and not tipo_var_obj.is_ponteiro and not tipo_var_obj.campos:
            if tipo_exp_obj.nome_base in {'real', 'inteiro'} and not tipo_exp_obj.is_ponteiro and not tipo_exp_obj.campos:
                return True # Permite inteiro para real, real para real, inteiro para inteiro
            return False

        # literal <- literal
        if tipo_var_obj.nome_base == 'literal' and not tipo_var_obj.is_ponteiro and not tipo_var_obj.campos:
            return tipo_exp_obj.nome_base == 'literal' and not tipo_exp_obj.is_ponteiro and not tipo_exp_obj.campos

        # logico <- logico
        if tipo_var_obj.nome_base == 'logico' and not tipo_var_obj.is_ponteiro and not tipo_var_obj.campos:
            return tipo_exp_obj.nome_base == 'logico' and not tipo_exp_obj.is_ponteiro and not tipo_exp_obj.campos

        # registro <- registro (com mesmo nome de tipo)
        if tipo_var_obj.campos and tipo_exp_obj.campos:
            return tipo_var_obj.nome_base == tipo_exp_obj.nome_base # Mesmo nome de tipo de registro
        
        return False

    # --- Listener Methods ---

    # Escopo para programa
    def enterPrograma(self, ctx:LAParser.ProgramaContext):
        self.empilhar_escopo()

    def exitPrograma(self, ctx:LAParser.ProgramaContext):
        self.desempilhar_escopo()

    # Escopo para procedimentos e funções
    def enterDeclaracao_procedimento(self, ctx:LAParser.Declaracao_procedimentoContext):
        nome_proc = ctx.IDENT().getText()
        # Verificar se já declarado no escopo atual antes de empilhar um novo escopo
        if self.pilha_tabelas[-1].buscar(nome_proc):
            self.erros.append(f"Linha {ctx.IDENT().symbol.line}: identificador {nome_proc} ja declarado anteriormente")
            return

        self.empilhar_escopo() # Novo escopo para o procedimento
        
        params = []
        if ctx.parametros():
            for param_ctx in ctx.parametros().parametro():
                param_name = param_ctx.IDENT().getText()
                param_type_obj = self.get_tipo_from_ctx(param_ctx.tipo_base() or param_ctx.tipo_identificado())
                if param_type_obj.nome_base == 'indefinido':
                    self.erros.append(f"Linha {param_ctx.IDENT().symbol.line}: tipo {param_ctx.tipo_base().getText() if param_ctx.tipo_base() else param_ctx.tipo_identificado().getText()} nao declarado")
                eh_var = param_ctx.VAR() is not None
                params.append((param_name, param_type_obj, eh_var))
                # Adicionar parâmetro à tabela de símbolos do escopo do procedimento
                self.adicionar_simbolo_escopo_atual(Simbolo(param_name, param_type_obj, 'variavel'), param_ctx.IDENT().getSymbol())

        simbolo_proc = Simbolo(nome_proc, TipoLA('void'), 'procedimento', params=params)
        self.pilha_tabelas[-2].adicionar(simbolo_proc) # Adiciona no escopo PARENT

    def exitDeclaracao_procedimento(self, ctx:LAParser.Declaracao_procedimentoContext):
        self.desempilhar_escopo()

    def enterDeclaracao_funcao(self, ctx:LAParser.Declaracao_funcaoContext):
        nome_func = ctx.IDENT().getText()
        if self.pilha_tabelas[-1].buscar(nome_func):
            self.erros.append(f"Linha {ctx.IDENT().symbol.line}: identificador {nome_func} ja declarado anteriormente")
            return

        tipo_retorno_obj = self.get_tipo_from_ctx(ctx.tipo_base())
        if tipo_retorno_obj.nome_base == 'indefinido':
            self.erros.append(f"Linha {ctx.tipo_base().start.line}: tipo {ctx.tipo_base().getText()} nao declarado")
        self.tipo_retorno_atual = tipo_retorno_obj # Define o tipo de retorno esperado

        self.empilhar_escopo() # Novo escopo para a função

        params = []
        if ctx.parametros():
            for param_ctx in ctx.parametros().parametro():
                param_name = param_ctx.IDENT().getText()
                param_type_obj = self.get_tipo_from_ctx(param_ctx.tipo_base() or param_ctx.tipo_identificado())
                if param_type_obj.nome_base == 'indefinido':
                    self.erros.append(f"Linha {param_ctx.IDENT().symbol.line}: tipo {param_ctx.tipo_base().getText() if param_ctx.tipo_base() else param_ctx.tipo_identificado().getText()} nao declarado")
                eh_var = param_ctx.VAR() is not None
                params.append((param_name, param_type_obj, eh_var))
                # Adicionar parâmetro à tabela de símbolos do escopo da função
                self.adicionar_simbolo_escopo_atual(Simbolo(param_name, param_type_obj, 'variavel'), param_ctx.IDENT().getSymbol())

        simbolo_func = Simbolo(nome_func, tipo_retorno_obj, 'funcao', params=params, tipo_retorno=tipo_retorno_obj)
        self.pilha_tabelas[-2].adicionar(simbolo_func) # Adiciona no escopo PARENT

    def exitDeclaracao_funcao(self, ctx:LAParser.Declaracao_funcaoContext):
        self.tipo_retorno_atual = None # Limpa o tipo de retorno ao sair da função
        self.desempilhar_escopo()

    # Escopo para blocos de comando (como `comandos` dentro de `se`, `para`, `enquanto`)
    # É importante notar que na sua gramática 'comandos' pode conter 'declaracao'.
    # Isso sugere que 'declare' pode criar um novo escopo implícito, mas a gramática
    # LA não tipicamente permite declarações aninhadas em qualquer bloco.
    # Para simplicidade e aderência ao LA, vamos considerar que "comandos" não cria um novo escopo,
    # exceto se houver um `declare` dentro, que já é tratado.
    # Se declaracoes_locais for aninhado, ele criará seu próprio escopo.

    def enterDeclaracoes_locais(self, ctx:LAParser.Declaracoes_locaisContext):
        self.empilhar_escopo() # Novo escopo para declarações locais

    def exitDeclaracoes_locais(self, ctx:LAParser.Declaracoes_locaisContext):
        self.desempilhar_escopo()

    # --- Tratamento de Declarações ---

    def get_tipo_from_ctx(self, tipo_ctx):
        if tipo_ctx is None:
            return TipoLA('indefinido')

        is_ponteiro = tipo_ctx.CIRCUNFLEXO() is not None
        
        if isinstance(tipo_ctx, LAParser.TipoPrimitivoContext):
            nome_base = tipo_ctx.tipo_base().getText().replace('^', '')
            if nome_base not in TIPOS_PRIMITIVOS:
                return TipoLA('indefinido') # Tipo primitivo inválido
            return TipoLA(nome_base, is_ponteiro=is_ponteiro)

        elif isinstance(tipo_ctx, LAParser.TipoIdentificadoContext):
            nome_tipo = tipo_ctx.IDENT().getText()
            simbolo_tipo = self.buscar_simbolo(nome_tipo)
            if not simbolo_tipo or simbolo_tipo.categoria != 'tipo':
                # Se o tipo não for encontrado ou não for uma declaração de tipo
                return TipoLA('indefinido')
            # Retorna o tipo customizado, adicionando a informação de ponteiro se houver
            return TipoLA(simbolo_tipo.tipo.nome_base, is_ponteiro=is_ponteiro or simbolo_tipo.tipo.is_ponteiro, campos=simbolo_tipo.tipo.campos)
        
        elif isinstance(tipo_ctx, LAParser.TipoRegistroContext):
            # Cria um tipo anônimo de registro ou usa um nome se for declarado com 'tipo'
            campos = {}
            for campo_ctx in tipo_ctx.tipo_registro().lista_campos().campo():
                campo_base_type = self.get_tipo_from_ctx(campo_ctx.tipo_base())
                if campo_base_type.nome_base == 'indefinido':
                    self.erros.append(f"Linha {campo_ctx.start.line}: tipo {campo_ctx.tipo_base().getText()} nao declarado para campo")

                for ident_ctx in campo_ctx.IDENT():
                    if ident_ctx.getText() in campos:
                         self.erros.append(f"Linha {ident_ctx.symbol.line}: campo {ident_ctx.getText()} ja declarado no registro")
                    campos[ident_ctx.getText()] = campo_base_type
            return TipoLA('registro', campos=campos) # Nome base 'registro' para registros anônimos
        
        return TipoLA('indefinido')


    def enterDeclaracao(self, ctx:LAParser.DeclaracaoContext):
        for var_ctx in ctx.lista_variaveis().variavel():
            tipo_la_obj = self.get_tipo_from_ctx(var_ctx.tipo())
            
            if tipo_la_obj.nome_base == 'indefinido':
                # Só reporta o erro se o tipo base não for reconhecido como um registro já declarado
                # Se o tipo for identificado e não existir, o get_tipo_from_ctx já adiciona o erro.
                if isinstance(var_ctx.tipo(), LAParser.TipoIdentificadoContext):
                    nome_tipo = var_ctx.tipo().IDENT().getText()
                    simbolo_tipo = self.buscar_simbolo(nome_tipo)
                    if not simbolo_tipo or simbolo_tipo.categoria != 'tipo':
                        self.erros.append(f"Linha {self.linha_token(var_ctx.tipo().start)}: tipo {nome_tipo} nao declarado")
                else: # Deve ser tipo primitivo inválido
                    self.erros.append(f"Linha {self.linha_token(var_ctx.tipo().start)}: tipo {var_ctx.tipo().getText()} nao declarado")

            for i in range(var_ctx.IDENT().__len__()):
                nome_var = var_ctx.IDENT(i).getText()
                token_var = var_ctx.IDENT(i).getSymbol()
                self.adicionar_simbolo_escopo_atual(Simbolo(nome_var, tipo_la_obj, 'variavel'), token_var)

    def enterDeclaracao_constante(self, ctx:LAParser.Declaracao_constanteContext):
        nome_const = ctx.IDENT().getText()
        token_const = ctx.IDENT().getSymbol()
        tipo_const_ctx = ctx.tipo_base()
        tipo_const_obj = self.get_tipo_from_ctx(tipo_const_ctx)

        if tipo_const_obj.nome_base == 'indefinido':
             self.erros.append(f"Linha {self.linha_token(tipo_const_ctx.start)}: tipo {tipo_const_ctx.getText()} nao declarado")

        # Verifica tipo do valor_constante e compatibilidade
        tipo_val = self.get_tipo_valor_constante(ctx.valor_constante())
        if not self.eh_compativel_atribuicao(tipo_const_obj, tipo_val):
            self.erros.append(f"Linha {self.linha_token(ctx.valor_constante().start)}: atribuicao de valor a constante {nome_const} nao compativel")
            
        self.adicionar_simbolo_escopo_atual(Simbolo(nome_const, tipo_const_obj, 'constante'), token_const)

    def get_tipo_valor_constante(self, ctx):
        if ctx.NUM_INT():
            return TipoLA('inteiro')
        elif ctx.NUM_REAL():
            return TipoLA('real')
        elif ctx.CADEIA():
            return TipoLA('literal')
        elif ctx.getText() in ('verdadeiro', 'falso'):
            return TipoLA('logico')
        return TipoLA('indefinido')

    def enterDeclaracao_tipo(self, ctx:LAParser.Declaracao_tipoContext):
        nome_tipo = ctx.IDENT().getText()
        token_tipo = ctx.IDENT().getSymbol()

        tipo_obj_declarado = None
        if ctx.tipo_registro():
            tipo_obj_declarado = self.get_tipo_from_ctx(ctx) # Isto irá gerar um TipoLA com campos
            tipo_obj_declarado.nome_base = nome_tipo # Atribui o nome do tipo ao registro
        elif ctx.tipo_identificado():
            # Um tipo pode ser um alias para outro tipo já existente
            base_type_name = ctx.tipo_identificado().IDENT().getText()
            simbolo_base_type = self.buscar_simbolo(base_type_name)
            if not simbolo_base_type or simbolo_base_type.categoria != 'tipo':
                self.erros.append(f"Linha {self.linha_token(ctx.tipo_identificado().start)}: tipo {base_type_name} nao declarado")
                tipo_obj_declarado = TipoLA('indefinido')
            else:
                tipo_obj_declarado = simbolo_base_type.tipo # Copia o objeto TipoLA do tipo base

        if tipo_obj_declarado:
            self.adicionar_simbolo_escopo_atual(Simbolo(nome_tipo, tipo_obj_declarado, 'tipo'), token_tipo)


    # --- Análise de Comandos ---

    def enterAtribuicao(self, ctx:LAParser.AtribuicaoContext):
        # Tratar identificadores simples e acesso a campos e ponteiros
        tipo_var_esq = None
        var_esq_token = None

        if ctx.IDENT():
            nome_var = ctx.IDENT().getText()
            var_esq_token = ctx.IDENT().getSymbol()
            simbolo = self.buscar_simbolo(nome_var)
            if not simbolo:
                self.erros.append(f"Linha {var_esq_token.line}: identificador {nome_var} nao declarado")
                return # Não pode continuar a análise de tipo sem o símbolo
            tipo_var_esq = simbolo.tipo

        elif ctx.acesso_campo():
            tipo_var_esq = self.tipo_acesso_campo(ctx.acesso_campo())
            var_esq_token = ctx.acesso_campo().start # Token do início do acesso ao campo

        elif ctx.CIRCUNFLEXO() and ctx.IDENT(): # Atribuição a um ponteiro desreferenciado
            nome_ponteiro = ctx.IDENT().getText()
            var_esq_token = ctx.IDENT().getSymbol()
            simbolo_ponteiro = self.buscar_simbolo(nome_ponteiro)
            if not simbolo_ponteiro:
                self.erros.append(f"Linha {var_esq_token.line}: identificador {nome_ponteiro} nao declarado")
                return
            if not simbolo_ponteiro.tipo.is_ponteiro:
                self.erros.append(f"Linha {var_esq_token.line}: uso indevido de ponteiro com identificador {nome_ponteiro}")
                return
            tipo_var_esq = TipoLA(simbolo_ponteiro.tipo.nome_base) # Tipo desreferenciado

        if not tipo_var_esq or tipo_var_esq.nome_base == 'indefinido':
            # Erro de variável não declarada ou tipo indefinido já reportado, ou erro de acesso_campo
            return

        tipo_exp_dir = self.tipo_expressao(ctx.expressao())

        if tipo_exp_dir.nome_base == 'indefinido':
            # Erro na expressão da direita já foi reportado
            return

        if not self.eh_compativel_atribuicao(tipo_var_esq, tipo_exp_dir):
            self.erros.append(f"Linha {self.linha_token(var_esq_token)}: atribuicao nao compativel para {var_esq_token.text}")

    def tipo_acesso_campo(self, ctx: LAParser.Acesso_campoContext):
        # Inicia com o primeiro identificador (nome do registro)
        nome_registro = ctx.IDENT(0).getText()
        simbolo_registro = self.buscar_simbolo(nome_registro)

        if not simbolo_registro:
            self.erros.append(f"Linha {ctx.IDENT(0).symbol.line}: identificador {nome_registro} nao declarado")
            return TipoLA('indefinido')

        current_type = simbolo_registro.tipo
        if not current_type or not current_type.campos:
            self.erros.append(f"Linha {ctx.IDENT(0).symbol.line}: identificador {nome_registro} nao e um registro ou tipo de registro")
            return TipoLA('indefinido')

        # Percorre os campos
        for i in range(1, len(ctx.IDENT())):
            nome_campo = ctx.IDENT(i).getText()
            if current_type and current_type.campos and nome_campo in current_type.campos:
                current_type = current_type.campos[nome_campo]
            else:
                self.erros.append(f"Linha {ctx.IDENT(i).symbol.line}: campo {nome_campo} nao existe no registro {nome_registro}")
                return TipoLA('indefinido')
        
        return current_type # Retorna o TipoLA do campo final

    def enterLeitura(self, ctx:LAParser.LeituraContext):
        for item_ctx in ctx.lista_identificadores().children:
            if isinstance(item_ctx, TerminalNode): # Vírgulas ou outros terminais
                continue

            # IDENT ou acesso_campo
            nome_ou_acesso = item_ctx.getText()
            if isinstance(item_ctx, LAParser.Acesso_campoContext):
                tipo_ident = self.tipo_acesso_campo(item_ctx)
                if tipo_ident.nome_base == 'indefinido':
                    # Erro já reportado pelo tipo_acesso_campo
                    pass
            elif item_ctx.IDENT():
                nome_var = item_ctx.IDENT().getText()
                simbolo = self.buscar_simbolo(nome_var)
                if not simbolo:
                    self.erros.append(f"Linha {item_ctx.IDENT().symbol.line}: identificador {nome_var} nao declarado")
                # Não é necessário verificar o tipo, pois 'leia' pode ler qualquer tipo compatível

    def enterEscrita(self, ctx:LAParser.EscritaContext):
        for exp in ctx.expressao():
            tipo_exp = self.tipo_expressao(exp)
            if tipo_exp.nome_base == 'indefinido':
                # Erro já foi reportado na avaliação da expressão
                pass

    def enterChamada_procedimento(self, ctx:LAParser.Chamada_procedimentoContext):
        nome_proc = ctx.IDENT().getText()
        token_proc = ctx.IDENT().getSymbol()
        simbolo_proc = self.buscar_simbolo(nome_proc)

        if not simbolo_proc:
            self.erros.append(f"Linha {token_proc.line}: identificador {nome_proc} nao declarado")
            return
        if simbolo_proc.categoria != 'procedimento':
            self.erros.append(f"Linha {token_proc.line}: identificador {nome_proc} nao e um procedimento")
            return

        # Verificar argumentos
        argumentos = []
        if ctx.lista_expressao():
            for exp_ctx in ctx.lista_expressao().expressao():
                argumentos.append(self.tipo_expressao(exp_ctx))

        if len(argumentos) != len(simbolo_proc.params):
            self.erros.append(f"Linha {token_proc.line}: numero de argumentos incompativel com o procedimento {nome_proc}")
            return

        for i, (param_name, param_type, eh_var) in enumerate(simbolo_proc.params):
            arg_type = argumentos[i]
            # Se o parâmetro for 'var', o argumento deve ser um endereço (ponteiro) e o tipo base deve ser o mesmo
            if eh_var:
                # Precisa ser um acesso à memória, não um valor literal
                if not (isinstance(ctx.lista_expressao().expressao(i).fator(), LAParser.FatorContext) and
                        (ctx.lista_expressao().expressao(i).fator().IDENT() or ctx.lista_expressao().expressao(i).fator().acesso_campo())):
                    self.erros.append(f"Linha {self.linha_token(ctx.lista_expressao().expressao(i).start)}: argumento {i+1} para {nome_proc} nao e um endereco")
                elif not self.eh_compativel_argumento(param_type, arg_type): # Argumento eh_var deve ser do mesmo tipo
                    self.erros.append(f"Linha {self.linha_token(ctx.lista_expressao().expressao(i).start)}: tipo do argumento {i+1} incompativel com o parametro formal para {nome_proc}")
            else: # Parâmetro por valor
                if not self.eh_compativel_atribuicao(param_type, arg_type): # Usa a compatibilidade de atribuição
                    self.erros.append(f"Linha {self.linha_token(ctx.lista_expressao().expressao(i).start)}: tipo do argumento {i+1} incompativel com o parametro formal para {nome_proc}")
    
    # Adicionar uma nova função para verificar a compatibilidade de argumentos
    def eh_compativel_argumento(self, tipo_param, tipo_arg):
        if not tipo_param or not tipo_arg:
            return False

        # Endereço -> ponteiro
        if tipo_param.is_ponteiro and tipo_arg.is_ponteiro:
            return tipo_param.nome_base == tipo_arg.nome_base
        
        # Tipos primitivos e registros (exata correspondência)
        return tipo_param == tipo_arg or \
               (tipo_param.nome_base == 'real' and tipo_arg.nome_base == 'inteiro' and not tipo_param.is_ponteiro and not tipo_arg.is_ponteiro)


    def tipo_chamada_funcao(self, ctx:LAParser.Chamada_funcaoContext):
        nome_func = ctx.IDENT().getText()
        token_func = ctx.IDENT().getSymbol()
        simbolo_func = self.buscar_simbolo(nome_func)

        if not simbolo_func:
            self.erros.append(f"Linha {token_func.line}: identificador {nome_func} nao declarado")
            return TipoLA('indefinido')
        if simbolo_func.categoria != 'funcao':
            self.erros.append(f"Linha {token_func.line}: identificador {nome_func} nao e uma funcao")
            return TipoLA('indefinido')

        # Verificar argumentos
        argumentos = []
        if ctx.lista_expressao():
            for exp_ctx in ctx.lista_expressao().expressao():
                argumentos.append(self.tipo_expressao(exp_ctx))

        if len(argumentos) != len(simbolo_func.params):
            self.erros.append(f"Linha {token_func.line}: numero de argumentos incompativel com a funcao {nome_func}")
            return TipoLA('indefinido')

        for i, (param_name, param_type, eh_var) in enumerate(simbolo_func.params):
            arg_type = argumentos[i]
            if eh_var:
                if not (isinstance(ctx.lista_expressao().expressao(i).fator(), LAParser.FatorContext) and
                        (ctx.lista_expressao().expressao(i).fator().IDENT() or ctx.lista_expressao().expressao(i).fator().acesso_campo())):
                    self.erros.append(f"Linha {self.linha_token(ctx.lista_expressao().expressao(i).start)}: argumento {i+1} para {nome_func} nao e um endereco")
                elif not self.eh_compativel_argumento(param_type, arg_type):
                    self.erros.append(f"Linha {self.linha_token(ctx.lista_expressao().expressao(i).start)}: tipo do argumento {i+1} incompativel com o parametro formal para {nome_func}")
            else:
                if not self.eh_compativel_atribuicao(param_type, arg_type):
                    self.erros.append(f"Linha {self.linha_token(ctx.lista_expressao().expressao(i).start)}: tipo do argumento {i+1} incompativel com o parametro formal para {nome_func}")
        
        return simbolo_func.tipo_retorno # Retorna o tipo de retorno da função


    def enterRetorne(self, ctx:LAParser.RetorneContext):
        if not self.tipo_retorno_atual:
            self.erros.append(f"Linha {ctx.start.line}: comando retorne nao permitido neste escopo")
            return

        tipo_exp_retorno = self.tipo_expressao(ctx.expressao())
        if tipo_exp_retorno.nome_base == 'indefinido':
            return # Erro já reportado na expressão

        if not self.eh_compativel_atribuicao(self.tipo_retorno_atual, tipo_exp_retorno):
            self.erros.append(f"Linha {ctx.expressao().start.line}: tipo de retorno incompativel com o tipo declarado para a funcao")


# --- Função principal (main) ---

def main():
    if len(sys.argv) != 3:
        print("Uso: python3 analisador_semantico.py entrada.txt saida.txt")
        return

    arquivo_entrada = sys.argv[1]
    arquivo_saida = sys.argv[2]

    try:
        input_stream = FileStream(arquivo_entrada, encoding='utf-8')
        lexer = LALexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = LAParser(token_stream)

        # Remove o listener de erro padrão para evitar mensagens duplicadas
        parser.removeErrorListeners()
        lexer.removeErrorListeners()

        # O ANTLR gera automaticamente erros sintáticos.
        # Precisamos de um ErrorListener customizado para capturar esses erros
        # e adicioná-los à nossa lista de erros sem interromper a execução.
        # Isso já deve estar no seu T3, mas é bom reforçar.
        class CustomErrorListener(ErrorListener):
            def __init__(self, analyzer):
                super().__init__()
                self.analyzer = analyzer

            def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
                # Captura erros sintáticos e adiciona à lista de erros semânticos
                self.analyzer.erros.append(f"Linha {line}: erro sintatico proximo a '{offendingSymbol.text}'")

        error_listener = CustomErrorListener(AnalisadorSemantico(token_stream))
        parser.addErrorListener(error_listener)
        lexer.addErrorListener(error_listener)

        tree = parser.programa()

        analisador = AnalisadorSemantico(token_stream)
        walker = ParseTreeWalker()
        walker.walk(analisador, tree)

        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            for erro in sorted(set(analisador.erros)): # Usa set para remover duplicatas e sorted para ordem
                f.write(erro + '\n')
            f.write("Fim da compilacao\n")

    except FileNotFoundError:
        print(f"Erro: Arquivo '{arquivo_entrada}' nao encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    main()