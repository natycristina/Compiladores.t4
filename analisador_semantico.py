import sys
from antlr4 import *
from antlr4.error.ErrorListener import ErrorListener
# Correção: Importar ParserRuleContext diretamente de antlr4, não de antlr4.tree.Tree
from antlr4.tree.Tree import TerminalNode, ParseTreeWalker
from antlr4 import ParserRuleContext # Importação corrigida para ParserRuleContext

# Importa as classes geradas pelo ANTLR.
# Certifique-se de que 'LAParser.py', 'LALexer.py', 'LAListener.py'
# estejam no mesmo diretório ou acessíveis no PYTHONPATH.
from LAParser import LAParser
from LALexer import LALexer
from LAListener import LAListener

# Tipos primitivos da linguagem LA que são sempre válidos.
# 'endereco' é adicionado como um tipo implícito para operações com ponteiros.
TIPOS_PRIMITIVOS = {'literal', 'inteiro', 'real', 'logico', 'endereco'}

# Classe para representar uma entrada na tabela de símbolos.
# Armazena o nome, categoria (variável, função, tipo, etc.), informações de tipo e linha de declaração.
class SymbolEntry:
    def __init__(self, name, category, type_info, line):
        self.name = name
        self.category = category # Ex: 'variavel', 'constante', 'procedimento', 'funcao', 'tipo', 'parametro'
        self.type_info = type_info # Pode ser uma string ('inteiro'), ou um dicionário para registros/funções
        self.line = line # Linha onde o símbolo foi declarado

# Classe para gerenciar a tabela de símbolos e os escopos.
# Usa uma pilha de dicionários para representar os escopos aninhados.
class SymbolTable:
    def __init__(self):
        # A pilha de escopos, começando com o escopo global.
        self.scopes = [{}]

    # Adiciona um novo escopo (um novo dicionário) à pilha.
    def push_scope(self):
        self.scopes.append({})

    # Remove o escopo mais recente da pilha. Não remove o escopo global.
    def pop_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()

    # Declara um símbolo no escopo atual.
    # Retorna True se a declaração for bem-sucedida (símbolo não existia no escopo atual), False caso contrário.
    def declare_symbol(self, name, category, type_info, line):
        current_scope = self.scopes[-1]
        if name in current_scope:
            return False # Símbolo já declarado no escopo atual
        current_scope[name] = SymbolEntry(name, category, type_info, line)
        return True

    # Busca um símbolo, começando pelo escopo atual e subindo até o escopo global.
    # Retorna o objeto SymbolEntry se encontrado, None caso contrário.
    def lookup_symbol(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    # Retorna o dicionário de símbolos do escopo atual.
    def get_current_scope_symbols(self):
        return self.scopes[-1]

# Um Listener de Erros personalizado para capturar erros de sintaxe.
# No entanto, o foco principal deste trabalho são os erros semânticos.
class CustomErrorListener(ErrorListener):
    def __init__(self):
        super().__init__()
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        # Para este trabalho, vamos focar nos erros semânticos.
        # Erros de sintaxe podem ser ignorados ou registrados de forma diferente.
        pass

# A classe principal do analisador semântico, que estende LAListener.
# Ela percorre a árvore de parse e realiza verificações semânticas.
class AnalisadorSemantico(LAListener):
    def __init__(self, token_stream):
        self.symbol_table = SymbolTable()
        self.erros = [] # Lista para armazenar todos os erros semânticos encontrados
        self.tokens = token_stream # Stream de tokens para obter informações de linha

        # Variáveis de estado para rastrear o contexto do analisador
        self.current_function_return_type = None # Armazena o tipo de retorno da função atual para verificação do 'retorne'
        self.in_function_or_procedure = 0 # Contador para saber se estamos dentro de um proc/função (para 'retorne')

    # Retorna o número da linha de um token.
    def linha_token(self, token):
        if token:
            return token.line
        return -1

    # Verifica a compatibilidade entre dois tipos para uma atribuição (LHS <- RHS).
    # tipo_var: o tipo da variável no lado esquerdo da atribuição.
    # tipo_exp: o tipo da expressão no lado direito da atribuição.
    def eh_compativel_atribuicao(self, tipo_var, tipo_exp):
        if tipo_var is None or tipo_exp is None:
            return False

        # Compatibilidade exata (ex: 'inteiro' == 'inteiro')
        if tipo_var == tipo_exp:
            return True
        
        # Promoção numérica: inteiro pode ser atribuído a real
        if tipo_var == 'real' and tipo_exp == 'inteiro':
            return True
        
        # Atribuição de ponteiro: ponteiro <- endereço
        # 'tipo_var' será uma string como '^inteiro', e 'tipo_exp' será 'endereco'.
        if isinstance(tipo_var, str) and tipo_var.startswith('^') and tipo_exp == 'endereco':
            # Uma verificação mais rigorosa exigiria que o tipo base do ponteiro
            # corresponda ao tipo da variável cujo endereço está sendo tomado, mas simplificamos aqui.
            return True 

        # Atribuição de registro: registro <- registro (com mesmo nome de tipo)
        # tipo_var e tipo_exp são os nomes dos tipos de registro.
        # Isto se aplica a registros nomeados (ex: 'PontoXYZ').
        if isinstance(tipo_var, str) and isinstance(tipo_exp, str):
            sym_var_type_def = self.symbol_table.lookup_symbol(tipo_var)
            sym_exp_type_def = self.symbol_table.lookup_symbol(tipo_exp)

            if sym_var_type_def and sym_exp_type_def:
                if (sym_var_type_def.category == 'tipo' and
                    isinstance(sym_var_type_def.type_info, dict) and
                    sym_var_type_def.type_info.get('category') == 'registro') and \
                   (sym_exp_type_def.category == 'tipo' and
                    isinstance(sym_exp_type_def.type_info, dict) and
                    sym_exp_type_def.type_info.get('category') == 'registro'):
                    # Nomes dos tipos de registro devem ser os mesmos para compatibilidade por nome
                    return tipo_var == tipo_exp
        
        # Compatibilidade para registros inline (anônimos) - por estrutura, se permitido pela linguagem.
        # Se tipo_var e tipo_exp são dicionários que representam registros inline.
        if isinstance(tipo_var, dict) and tipo_var.get('category') == 'registro_inline' and \
           isinstance(tipo_exp, dict) and tipo_exp.get('category') == 'registro_inline':
            # Para simplificar, vamos exigir compatibilidade exata da estrutura.
            # Em um compilador real, isso envolveria comparar todos os campos e seus tipos recursivamente.
            # Aqui, para o T4, assumiremos que registros inline *não* são compatíveis entre si
            # a menos que sejam a mesma referência de objeto (o que não acontece com cópias de dicionário).
            # Se a intenção for compatibilidade estrutural para inline, esta lógica precisaria ser expandida.
            # A menos que explicitamente exigido, assume-se que inline records não são intercambiáveis por atribuição.
            return False # Registros inline não são compatíveis entre si por atribuição direta, apenas campos.

        return False

    # Helper para resolver o tipo de um L-value (lado esquerdo de atribuição/leitura).
    # Lida com IDENT (TerminalNode), Acesso_campoContext, e desreferenciação de ponteiro (^IDENT).
    def resolve_lvalue_type(self, lvalue_ctx):
        # Caso 1: Identificador simples (TerminalNode IDENT)
        if isinstance(lvalue_ctx, TerminalNode) and lvalue_ctx.getSymbol().type == LAParser.IDENT:
            name = lvalue_ctx.getText()
            sym_entry = self.symbol_table.lookup_symbol(name)
            if sym_entry is None:
                self.erros.append(f"Linha {self.linha_token(lvalue_ctx.getSymbol())}: identificador {name} nao declarado")
                return None
            return sym_entry.type_info # Pode ser string (primitivo, nome de tipo) ou dict (registro inline)

        # Caso 2: Acesso a campo (Acesso_campoContext)
        elif isinstance(lvalue_ctx, LAParser.Acesso_campoContext):
            base_name = lvalue_ctx.IDENT(0).getText()
            sym_entry = self.symbol_table.lookup_symbol(base_name)
            if sym_entry is None:
                self.erros.append(f"Linha {self.linha_token(lvalue_ctx.IDENT(0).getSymbol())}: identificador {base_name} nao declarado")
                return None
            
            # current_type_def_or_name pode ser uma string (nome de tipo) ou um dicionário (registro inline)
            current_type_def_or_name = sym_entry.type_info 
            
            # Obter a definição do registro (campos)
            current_record_fields = {}
            if isinstance(current_type_def_or_name, str): # É um nome de tipo (pode ser um registro nomeado ou ponteiro para ele)
                if current_type_def_or_name.startswith('^'):
                    base_type_name_for_record = current_type_def_or_name[1:] # Desreferencia o ponteiro
                else:
                    base_type_name_for_record = current_type_def_or_name

                record_type_entry = self.symbol_table.lookup_symbol(base_type_name_for_record)
                
                if (record_type_entry is None or
                    record_type_entry.category != 'tipo' or
                    not isinstance(record_type_entry.type_info, dict) or
                    record_type_entry.type_info.get('category') != 'registro'):
                    self.erros.append(f"Linha {self.linha_token(lvalue_ctx.IDENT(0).getSymbol())}: acesso de campo invalido em '{lvalue_ctx.getText()}' - '{current_type_def_or_name}' nao eh um registro ou ponteiro para registro")
                    return None
                current_record_fields = record_type_entry.type_info.get('campos', {})
            elif isinstance(current_type_def_or_name, dict) and current_type_def_or_name.get('category') == 'registro_inline':
                # É um registro inline diretamente. Use seus campos.
                current_record_fields = current_type_def_or_name.get('campos', {})
            else:
                self.erros.append(f"Linha {self.linha_token(lvalue_ctx.IDENT(0).getSymbol())}: identificador {base_name} nao eh um registro ou ponteiro para registro para acesso de campo")
                return None

            resolved_field_type = None
            # Itera sobre os campos aninhados (IDENT(1), IDENT(2), etc.)
            for i in range(1, len(lvalue_ctx.IDENT())):
                field_ident_token = lvalue_ctx.IDENT(i).getSymbol()
                field_name = field_ident_token.text
                
                if field_name not in current_record_fields:
                    self.erros.append(f"Linha {self.linha_token(field_ident_token)}: campo '{field_name}' nao existe no registro")
                    return None
                
                resolved_field_type = current_record_fields[field_name]['type']
                
                # Se o campo acessado é ele próprio um registro (nomeado ou inline),
                # atualizamos `current_record_fields` para a próxima iteração de campo.
                if isinstance(resolved_field_type, str): # Nome de um tipo, pode ser um registro nomeado
                    next_record_entry = self.symbol_table.lookup_symbol(resolved_field_type)
                    if (next_record_entry and next_record_entry.category == 'tipo' and
                        isinstance(next_record_entry.type_info, dict) and
                        next_record_entry.type_info.get('category') == 'registro'):
                        current_record_fields = next_record_entry.type_info.get('campos', {})
                    else: # Não é um registro nomeado, então a cadeia de acesso termina aqui.
                        break
                elif isinstance(resolved_field_type, dict) and resolved_field_type.get('category') == 'registro_inline':
                    # É um registro inline aninhado.
                    current_record_fields = resolved_field_type.get('campos', {})
                else: # Não é um registro (nem nomeado, nem inline), então a cadeia de acesso termina.
                    break
            
            return resolved_field_type # Retorna o tipo do último campo acessado.
            
        return None # Contexto de L-value não reconhecido.

    # Determina o tipo de uma expressão.
    # Percorre recursivamente a árvore da expressão, aplicando regras de tipo.
    def tipo_expressao(self, ctx):
        from LAParser import LAParser # Importa LAParser localmente para verificações de tipo de contexto

        # Expressão lógica (ou, e)
        if isinstance(ctx, LAParser.Expressao_logicaContext):
            tipos = [self.tipo_expressao(child) for child in ctx.expressao_relacional()]
            tipos = [t for t in tipos if t is not None] # Filtra tipos None (indicam erro anterior)

            if not tipos: return None

            if len(tipos) == 1:
                return tipos[0]
            
            # Todos os operandos devem ser lógicos para operadores 'e'/'ou'.
            for t in tipos:
                if t != 'logico':
                     self.erros.append(f"Linha {ctx.start.line}: operacao logica nao compativel com tipo '{t}'")
                     return None # Incompatível
            return 'logico'

        # Expressão relacional (>, <, =, >=, <=, <>)
        elif isinstance(ctx, LAParser.Expressao_relacionalContext):
            if ctx.getChildCount() == 1:
                return self.tipo_expressao(ctx.expressao_aritmetica(0))
            else:
                tipo_esq = self.tipo_expressao(ctx.expressao_aritmetica(0))
                tipo_dir = self.tipo_expressao(ctx.expressao_aritmetica(1))
                
                if tipo_esq is None or tipo_dir is None: return None

                # Operadores relacionais retornam 'logico' se os tipos são compatíveis.
                # Números (inteiro, real) são compatíveis entre si.
                # Outros tipos são compatíveis se forem exatamente o mesmo tipo (e.g., literal == literal).
                if (tipo_esq in ('inteiro','real') and tipo_dir in ('inteiro','real')) or \
                   (tipo_esq == tipo_dir):
                    return 'logico'
                else:
                    self.erros.append(f"Linha {ctx.start.line}: incompatibilidade de tipo em expressao relacional. Comparando '{tipo_esq}' com '{tipo_dir}'")
                    return None

        # Expressão aritmética (+, -)
        elif isinstance(ctx, LAParser.Expressao_aritmeticaContext):
            tipos = [self.tipo_expressao(term) for term in ctx.termo()]
            tipos = [t for t in tipos if t is not None]

            if not tipos: return None

            tipo_acumulado = tipos[0]
            for i, t in enumerate(tipos[1:]):
                op_token = ctx.getChild(2 * i + 1) # Operador (+ ou -)
                op_text = op_token.getText()
                
                if tipo_acumulado in ('inteiro','real') and t in ('inteiro','real'):
                    # Promoção para real se um dos tipos for real.
                    tipo_acumulado = 'real' if 'real' in (tipo_acumulado, t) else 'inteiro'
                elif tipo_acumulado == 'literal' and t == 'literal' and op_text == '+':
                    # Concatenação de literais apenas com '+'.
                    tipo_acumulado = 'literal'
                else:
                    self.erros.append(f"Linha {ctx.start.line}: operacao aritmetica nao compativel entre '{tipo_acumulado}' e '{t}'")
                    return None # Tipos incompatíveis para a operação
            return tipo_acumulado

        # Termo (*, /, %)
        elif isinstance(ctx, LAParser.TermoContext):
            tipos = [self.tipo_expressao(fat) for fat in ctx.fator()]
            tipos = [t for t in tipos if t is not None]

            if not tipos: return None

            tipo_acumulado = tipos[0]
            for t in tipos[1:]:
                if tipo_acumulado in ('inteiro','real') and t in ('inteiro','real'):
                    tipo_acumulado = 'real' if 'real' in (tipo_acumulado, t) else 'inteiro'
                else:
                    self.erros.append(f"Linha {ctx.start.line}: operacao aritmetica nao compativel entre '{tipo_acumulado}' e '{t}'")
                    return None
            return tipo_acumulado

        # Fator (identificadores, literais, parênteses, unários, chamadas de função, endereços)
        elif isinstance(ctx, LAParser.FatorContext):
            # Prioridade para operadores unários e desreferenciação, acessos compostos, etc.
            
            # Unary minus and 'nao'
            if ctx.getChildCount() == 2:
                first_child = ctx.getChild(0)
                if isinstance(first_child, TerminalNode):
                    first_child_text = first_child.getText().lower()
                    if first_child_text == '-':
                        t = self.tipo_expressao(ctx.fator())
                        if t in ('inteiro', 'real'): return t
                        self.erros.append(f"Linha {ctx.start.line}: operacao de negacao unaria nao compativel com tipo '{t}'")
                        return None
                    elif first_child_text == 'nao':
                        t = self.tipo_expressao(ctx.fator())
                        if t == 'logico': return 'logico'
                        self.erros.append(f"Linha {ctx.start.line}: operacao de negacao logica nao compativel com tipo '{t}'")
                        return None
                    elif first_child_text == '&': # '&' (IDENT | acesso_campo)
                        operand_ctx = ctx.getChild(1) 
                        # resolve_lvalue_type já trata a verificação de declaração para IDENT e acesso_campo
                        resolved_type = self.resolve_lvalue_type(operand_ctx) 
                        if resolved_type is None: # Erro já reportado por resolve_lvalue_type
                            return None
                        return 'endereco' # O resultado de '&' é sempre do tipo 'endereco'
                    elif first_child_text == '^': # CIRCUNFLEXO IDENT
                        ident_node = ctx.getChild(1) # O IDENT após CIRCUNFLEXO
                        if isinstance(ident_node, TerminalNode) and ident_node.getSymbol().type == LAParser.IDENT:
                            name = ident_node.getText()
                            sym_entry = self.symbol_table.lookup_symbol(name)
                            if sym_entry is None:
                                self.erros.append(f"Linha {self.linha_token(ident_node.getSymbol())}: identificador {name} nao declarado")
                                return None
                            if not (isinstance(sym_entry.type_info, str) and sym_entry.type_info.startswith('^')):
                                self.erros.append(f"Linha {self.linha_token(first_child.getSymbol())}: identificador {name} nao eh um ponteiro para ser desreferenciado")
                                return None
                            return sym_entry.type_info[1:] # Retorna o tipo base do ponteiro
                        else:
                            self.erros.append(f"Linha {self.linha_token(first_child.getSymbol())}: expressao invalida apos '^'")
                            return None

            # Parenthesized expression
            if ctx.ABREPAR() and ctx.expressao() and ctx.FECHAPAR():
                return self.tipo_expressao(ctx.expressao())

            # Function calls and specific operations (potencia, subliteral)
            if ctx.chamada_funcao():
                return self.tipo_funcao(ctx.chamada_funcao())
            
            if ctx.potencia():
                exp1_type = self.tipo_expressao(ctx.potencia().expressao(0))
                exp2_type = self.tipo_expressao(ctx.potencia().expressao(1))

                if exp1_type in ('inteiro', 'real') and exp2_type in ('inteiro', 'real'):
                    return 'real' if 'real' in (exp1_type, exp2_type) else 'inteiro'
                else:
                    self.erros.append(f"Linha {ctx.start.line}: operacao 'pot' nao compativel com tipos '{exp1_type}' e '{exp2_type}'")
                    return None

            if ctx.subliteral():
                exp_type = self.tipo_expressao(ctx.subliteral().expressao())
                if exp_type == 'literal':
                    return 'literal'
                else:
                    self.erros.append(f"Linha {ctx.start.line}: operacao 'subLiteral' espera um literal como primeiro argumento, encontrado '{exp_type}'")
                    return None

            # Accessing fields
            if ctx.acesso_campo():
                return self.resolve_lvalue_type(ctx.acesso_campo())

            # Simple identifiers/literals (last, as they are general and might be caught by other checks first)
            if ctx.IDENT(): # This is for the simple 'IDENT' alternative in fator
                return self.resolve_lvalue_type(ctx.IDENT()) # Passa o TerminalNode IDENT
            
            if ctx.NUM_INT():
                return 'inteiro'
            if ctx.NUM_REAL():
                return 'real'
            if ctx.CADEIA():
                return 'literal'
            if ctx.getText() in ('verdadeiro', 'falso'): # Booleans
                return 'logico'

            return None # Fator not recognized, should indicate an error if reached here.

        # Casos base para as regras de expressão (sempre devem descer para o próximo nível)
        elif isinstance(ctx, LAParser.ExpressaoContext):
            return self.tipo_expressao(ctx.expressao_logica())
        elif isinstance(ctx, LAParser.Expressao_logicaContext):
            # A regra expressao_logica pode ter mais de um expressao_relacional
            # Se tiver apenas um, retorna o tipo dele.
            if len(ctx.expressao_relacional()) > 0:
                return self.tipo_expressao(ctx.expressao_relacional()[0])
            return None # Nenhuma expressao relacional, erro ou expressao vazia
        elif isinstance(ctx, LAParser.Expressao_relacionalContext):
            # A regra expressao_relacional sempre tem pelo menos um expressao_aritmetica
            return self.tipo_expressao(ctx.expressao_aritmetica(0))
        elif isinstance(ctx, LAParser.Expressao_aritmeticaContext):
            # A regra expressao_aritmetica sempre tem pelo menos um termo
            return self.tipo_expressao(ctx.termo()[0])
        elif isinstance(ctx, LAParser.TermoContext):
            # A regra termo sempre tem pelo menos um fator
            return self.tipo_expressao(ctx.fator()[0])
        
        return None # Tipo desconhecido ou erro


    # --- Métodos Listener para Verificações Semânticas ---

    # Gerenciamento de escopo para o programa principal.
    def enterPrograma(self, ctx:LAParser.ProgramaContext):
        self.symbol_table.push_scope() # Inicia o escopo global.

    def exitPrograma(self, ctx:LAParser.ProgramaContext):
        self.symbol_table.pop_scope() # Sai do escopo global.

    # Gerenciamento de escopo e declaração para procedimentos.
    def enterDeclaracao_procedimento(self, ctx:LAParser.Declaracao_procedimentoContext):
        nome_proc = ctx.IDENT().getText()
        line = self.linha_token(ctx.IDENT().getSymbol())
        
        # Coleta os tipos dos parâmetros para a assinatura do procedimento.
        params = []
        if ctx.parametros():
            for param_ctx in ctx.parametros().parametro():
                param_type = None
                # A regra 'parametro' é 'IDENT ':' (tipo_base | tipo_identificado)'
                if param_ctx.tipo_base():
                    param_type = param_ctx.tipo_base().getText()
                elif param_ctx.tipo_identificado():
                    param_type = param_ctx.tipo_identificado().getText()
                
                param_name = param_ctx.IDENT().getText()
                param_line = self.linha_token(param_ctx.IDENT().getSymbol())
                
                if param_type:
                    params.append(param_type)

        # Declara o procedimento no escopo atual (escopo englobante).
        if not self.symbol_table.declare_symbol(nome_proc, 'procedimento', {'parametros': params, 'retorno': 'void'}, line):
            self.erros.append(f"Linha {line}: identificador {nome_proc} ja declarado anteriormente")

        # Entra em um novo escopo para os parâmetros do procedimento e variáveis locais.
        self.symbol_table.push_scope()
        self.in_function_or_procedure += 1 # Incrementa contador de escopo de função/proc

        # Declara os parâmetros no novo escopo (do procedimento).
        if ctx.parametros():
            for param_ctx in ctx.parametros().parametro():
                param_name = param_ctx.IDENT().getText()
                param_line = self.linha_token(param_ctx.IDENT().getSymbol())
                param_type = None
                if param_ctx.tipo_base():
                    param_type = param_ctx.tipo_base().getText()
                elif param_ctx.tipo_identificado():
                    param_type = param_ctx.tipo_identificado().getText()

                if param_type:
                    if not self.symbol_table.declare_symbol(param_name, 'parametro', param_type, param_line):
                        self.erros.append(f"Linha {param_line}: identificador {param_name} ja declarado anteriormente (parametro)")

    def exitDeclaracao_procedimento(self, ctx:LAParser.Declaracao_procedimentoContext):
        self.symbol_table.pop_scope() # Sai do escopo do procedimento.
        self.in_function_or_procedure -= 1 # Decrementa contador

    # Gerenciamento de escopo e declaração para funções.
    def enterDeclaracao_funcao(self, ctx:LAParser.Declaracao_funcaoContext):
        nome_func = ctx.IDENT().getText()
        line = self.linha_token(ctx.IDENT().getSymbol())
        return_type = ctx.tipo_base().getText() # Regra funcao: 'funcao' IDENT ... ':' tipo_base

        # Coleta os tipos dos parâmetros.
        params = []
        if ctx.parametros():
            for param_ctx in ctx.parametros().parametro():
                param_type = None
                if param_ctx.tipo_base():
                    param_type = param_ctx.tipo_base().getText()
                elif param_ctx.tipo_identificado():
                    param_type = param_ctx.tipo_identificado().getText()
                
                if param_type:
                    params.append(param_type)

        # Declara a função no escopo atual (englobante).
        if not self.symbol_table.declare_symbol(nome_func, 'funcao', {'parametros': params, 'retorno': return_type}, line):
            self.erros.append(f"Linha {line}: identificador {nome_func} ja declarado anteriormente")

        # Entra em um novo escopo para os parâmetros da função e variáveis locais.
        self.symbol_table.push_scope()
        self.in_function_or_procedure += 1
        self.current_function_return_type = return_type # Define o tipo de retorno esperado para 'retorne'

        # Declara os parâmetros no novo escopo (da função).
        if ctx.parametros():
            for param_ctx in ctx.parametros().parametro():
                param_name = param_ctx.IDENT().getText()
                param_line = self.linha_token(param_ctx.IDENT().getSymbol())
                param_type = None
                if param_ctx.tipo_base():
                    param_type = param_ctx.tipo_base().getText()
                elif param_ctx.tipo_identificado():
                    param_type = param_ctx.tipo_identificado().getText()

                if param_type:
                    if not self.symbol_table.declare_symbol(param_name, 'parametro', param_type, param_line):
                        self.erros.append(f"Linha {param_line}: identificador {param_name} ja declarado anteriormente (parametro)")

    def exitDeclaracao_funcao(self, ctx:LAParser.Declaracao_funcaoContext):
        self.symbol_table.pop_scope() # Sai do escopo da função.
        self.in_function_or_procedure -= 1
        self.current_function_return_type = None # Reseta o tipo de retorno esperado.

    # Lida com a declaração de variáveis (apenas 'declare lista_variaveis').
    def enterDeclaracao(self, ctx:LAParser.DeclaracaoContext):
        # A lógica detalhada de variáveis é movida para enterVariavel
        pass # Não faz nada aqui, deixa para enterVariavel.

    # Lida com a declaração de constantes.
    def enterDeclaracao_constante(self, ctx:LAParser.Declaracao_constanteContext):
        nome_const = ctx.IDENT().getText()
        line = self.linha_token(ctx.IDENT().getSymbol())
        tipo_const_text = ctx.tipo_base().getText() # Usa tipo_base na constante
        
        # Infere o tipo do valor literal atribuído à constante.
        valor_ctx = ctx.valor_constante()
        inferred_type = None
        if valor_ctx.CADEIA(): inferred_type = 'literal'
        elif valor_ctx.NUM_INT(): inferred_type = 'inteiro'
        elif valor_ctx.NUM_REAL(): inferred_type = 'real'
        elif valor_ctx.getText() in ('verdadeiro', 'falso'): inferred_type = 'logico'

        # Verifica a compatibilidade de atribuição para a inicialização da constante.
        if not self.eh_compativel_atribuicao(tipo_const_text, inferred_type):
            self.erros.append(f"Linha {line}: atribuicao nao compativel para constante {nome_const}")

        # Declara a constante no escopo atual.
        if not self.symbol_table.declare_symbol(nome_const, 'constante', tipo_const_text, line):
            self.erros.append(f"Linha {line}: identificador {nome_const} ja declarado anteriormente")

    # Lida com a declaração de tipos (registros ou aliases).
    def enterDeclaracao_tipo(self, ctx:LAParser.Declaracao_tipoContext):
        nome_tipo = ctx.IDENT().getText()
        line = self.linha_token(ctx.IDENT().getSymbol())

        # Não permite declarar um tipo com o mesmo nome de um tipo primitivo.
        if nome_tipo in TIPOS_PRIMITIVOS:
            self.erros.append(f"Linha {line}: identificador {nome_tipo} ja declarado anteriormente (nome de tipo primitivo)")

        # Verifica se o nome do tipo já está declarado no escopo atual.
        if nome_tipo in self.symbol_table.get_current_scope_symbols():
            self.erros.append(f"Linha {line}: identificador {nome_tipo} ja declarado anteriormente")
        else:
            type_info = {}
            if ctx.tipo_registro(): # Se for um tipo de registro.
                record_fields = {}
                lista_campos_ctx = None
                
                # Debug print: What is the child at index 1 of tipo_registro context?
                if len(ctx.tipo_registro().children) > 1:
                    potential_lista_campos_child = ctx.tipo_registro().getChild(1)
                    print(f"DEBUG: enterDeclaracao_tipo - tipo_registro child[1] type: {type(potential_lista_campos_child)}")
                    if isinstance(potential_lista_campos_child, ParserRuleContext):
                        print(f"DEBUG: enterDeclaracao_tipo - tipo_registro child[1] rule index: {potential_lista_campos_child.getRuleIndex()}")
                        print(f"DEBUG: enterDeclaracao_tipo - LAParser.RULE_lista_campos: {LAParser.RULE_lista_campos if hasattr(LAParser, 'RULE_lista_campos') else 'NOT FOUND (hasattr check)'}")
                        
                        if hasattr(LAParser, 'RULE_lista_campos') and potential_lista_campos_child.getRuleIndex() == LAParser.RULE_lista_campos:
                            lista_campos_ctx = potential_lista_campos_child
                        # Fallback to check by class name string if Rule Index fails (less reliable but for debug/fallback)
                        elif potential_lista_campos_child.__class__.__name__ == 'ListaCamposContext': 
                            lista_campos_ctx = potential_lista_campos_child
                
                if lista_campos_ctx is None:
                    # Original error message, now with more context provided by debug prints
                    error_msg = f"Linha {self.linha_token(ctx.tipo_registro().start)}: Erro interno SEMÂNTICO CRÍTICO: Não foi possível localizar o contexto 'lista_campos' para a declaração de registro. Verifique a gramática 'LA.g4' e a geração/importação dos arquivos ANTLR Python. Recomenda-se regenerar os arquivos ANTLR novamente após uma limpeza completa."
                    if 'potential_lista_campos_child' in locals():
                        error_msg += f" (Debug: Child at index 1 was of type {type(potential_lista_campos_child).__name__} and text '{potential_lista_campos_child.getText() if hasattr(potential_lista_campos_child, 'getText') else 'N/A'}')"
                    else:
                        error_msg += f" (Debug: Child at index 1 not found or unexpected structure)"
                    self.erros.append(error_msg)
                    return # Não é possível prosseguir sem o contexto.

                for campo_ctx in lista_campos_ctx.campo():
                    # A regra 'campo' é: IDENT (',' IDENT)* ':' tipo_base
                    field_type_text = campo_ctx.tipo_base().getText()
                    for field_ident_token in campo_ctx.IDENT():
                        field_name = field_ident_token.getText()
                        field_line = self.linha_token(field_ident_token.getSymbol())
                        
                        # Verifica se o tipo base do campo está declarado (se não for primitivo).
                        base_field_type = field_type_text.replace('^', '')
                        if base_field_type not in TIPOS_PRIMITIVOS:
                            sym_type_def = self.symbol_table.lookup_symbol(base_field_type)
                            if sym_type_def is None:
                                self.erros.append(f"Linha {self.linha_token(campo_ctx.tipo_base().start)}: tipo {base_field_type} nao declarado")
                            elif sym_type_def.category != 'tipo':
                                self.erros.append(f"Linha {self.linha_token(campo_ctx.tipo_base().start)}: identificador {base_field_type} nao eh um tipo valido")

                        # Verifica por nomes de campo duplicados dentro do mesmo registro.
                        if field_name in record_fields:
                            self.erros.append(f"Linha {field_line}: identificador de campo {field_name} ja declarado no registro {nome_tipo}")
                        record_fields[field_name] = {'type': field_type_text, 'line': field_line}
                type_info = {'category': 'registro', 'campos': record_fields}

            elif ctx.tipo_identificado(): # Se for um alias ou ponteiro para tipo.
                target_type = ctx.tipo_identificado().getText()
                is_pointer_type = target_type.startswith('^')
                base_target_type = target_type.replace('^','')

                # Verifica se o tipo alvo do alias/ponteiro está declarado.
                if base_target_type not in TIPOS_PRIMITIVOS:
                    sym_type_def = self.symbol_table.lookup_symbol(base_target_type)
                    if sym_type_def is None:
                        self.erros.append(f"Linha {self.linha_token(ctx.tipo_identificado().start)}: tipo {base_target_type} nao declarado")
                    elif sym_type_def.category != 'tipo':
                        self.erros.append(f"Linha {self.linha_token(ctx.tipo_identificado().start)}: identificador {base_target_type} nao eh um tipo valido")
                
                type_info = {'category': 'alias' if not is_pointer_type else 'ponteiro_para_tipo', 'target_type': target_type}
            
            self.symbol_table.declare_symbol(nome_tipo, 'tipo', type_info, line)

    # Lida com a declaração individual de variáveis dentro de uma lista_variaveis.
    def enterVariavel(self, ctx:LAParser.VariavelContext):
        # A regra 'variavel' é: IDENT (',' IDENT)* :' tipo
        declared_type_info = None
        type_ctx = ctx.tipo() # Get the 'tipo' context

        if isinstance(type_ctx, LAParser.TipoPrimitivoContext): # Usar isinstance para verificar o tipo do contexto
            declared_type_info = type_ctx.getText() # e.g., 'inteiro', '^real'
            base_declared_type = declared_type_info.replace('^','')
            if base_declared_type not in TIPOS_PRIMITIVOS:
                # Se não for um tipo primitivo, verifica se é um tipo declarado nomeado.
                sym_type_def = self.symbol_table.lookup_symbol(base_declared_type)
                if sym_type_def is None:
                    self.erros.append(f"Linha {self.linha_token(type_ctx.start)}: tipo {base_declared_type} nao declarado")
                    return # Não prossegue com tipo inválido.
                elif sym_type_def.category != 'tipo':
                    self.erros.append(f"Linha {self.linha_token(type_ctx.start)}: identificador {base_declared_type} nao eh um tipo valido")
                    return


        elif isinstance(type_ctx, LAParser.TipoIdentificadoContext): # Usar isinstance para verificar o tipo do contexto
            declared_type_info = type_ctx.getText() # e.g., 'MeuTipo', '^OutroTipo'
            base_declared_type = declared_type_info.replace('^','')
            
            # Verifica se o tipo identificado é um tipo declarado.
            sym_type_def = self.symbol_table.lookup_symbol(base_declared_type)
            if sym_type_def is None:
                self.erros.append(f"Linha {self.linha_token(type_ctx.start)}: tipo {base_declared_type} nao declarado")
                return
            elif sym_type_def.category != 'tipo':
                self.erros.append(f"Linha {self.linha_token(type_ctx.start)}: identificador {base_declared_type} nao eh um tipo valido")
                return

        elif isinstance(type_ctx, LAParser.TipoRegistroContext): # Usar isinstance para verificar o tipo do contexto
            # Processa a definição de registro inline.
            record_fields = {}
            lista_campos_ctx = None
            
            # Debug print: What is the child at index 1 of tipo_registro context?
            if len(type_ctx.children) > 1:
                potential_lista_campos_child = type_ctx.getChild(1)
                print(f"DEBUG: enterVariavel - tipo_registro child[1] type: {type(potential_lista_campos_child)}")
                if isinstance(potential_lista_campos_child, ParserRuleContext):
                    print(f"DEBUG: enterVariavel - tipo_registro child[1] rule index: {potential_lista_campos_child.getRuleIndex()}")
                    print(f"DEBUG: enterVariavel - LAParser.RULE_lista_campos: {LAParser.RULE_lista_campos if hasattr(LAParser, 'RULE_lista_campos') else 'NOT FOUND (hasattr check)'}")
                    
                    if hasattr(LAParser, 'RULE_lista_campos') and potential_lista_campos_child.getRuleIndex() == LAParser.RULE_lista_campos:
                        lista_campos_ctx = potential_lista_campos_child
                    # Fallback to check by class name string if Rule Index fails (less reliable but for debug/fallback)
                    elif potential_lista_campos_child.__class__.__name__ == 'ListaCamposContext': 
                        lista_campos_ctx = potential_lista_campos_child

            if lista_campos_ctx is None:
                # Original error message, now with more context provided by debug prints
                error_msg = f"Linha {self.linha_token(type_ctx.start)}: Erro interno SEMÂNTICO CRÍTICO: Não foi possível localizar o contexto 'lista_campos' para registro inline. Verifique a gramática 'LA.g4' e a geração/importação dos arquivos ANTLR Python. Recomenda-se regenerar os arquivos ANTLR novamente após uma limpeza completa."
                if 'potential_lista_campos_child' in locals():
                    error_msg += f" (Debug: Child at index 1 was of type {type(potential_lista_campos_child).__name__} and text '{potential_lista_campos_child.getText() if hasattr(potential_lista_campos_child, 'getText') else 'N/A'}')"
                else:
                    error_msg += f" (Debug: Child at index 1 not found or unexpected structure)"
                self.erros.append(error_msg)
                return # Sai para evitar AttributeError

            for campo_ctx in lista_campos_ctx.campo(): # Acessar .campo() diretamente do lista_campos_ctx
                field_type_text = campo_ctx.tipo_base().getText() # Campos de registro usam tipo_base
                for field_ident_token in campo_ctx.IDENT():
                    field_name = field_ident_token.getText()
                    field_line = self.linha_token(field_ident_token.getSymbol())
                    
                    base_field_type = field_type_text.replace('^', '')
                    if base_field_type not in TIPOS_PRIMITIVOS:
                        sym_type_def = self.symbol_table.lookup_symbol(base_field_type)
                        if sym_type_def is None:
                            self.erros.append(f"Linha {self.linha_token(campo_ctx.tipo_base().start)}: tipo {base_field_type} nao declarado")
                        elif sym_type_def.category != 'tipo':
                            self.erros.append(f"Linha {self.linha_token(campo_ctx.tipo_base().start)}: identificador {base_field_type} nao eh um tipo valido")

                    if field_name in record_fields:
                        self.erros.append(f"Linha {field_line}: identificador de campo {field_name} ja declarado no registro inline")
                    record_fields[field_name] = {'type': field_type_text, 'line': field_line}
            declared_type_info = {'category': 'registro_inline', 'campos': record_fields}

        else: # Tipo não reconhecido para a regra 'tipo'
            self.erros.append(f"Linha {self.linha_token(type_ctx.start)}: tipo invalido ou nao reconhecido")
            return

        # Agora declara as variáveis com a informação de tipo resolvida
        for ident_token in ctx.IDENT():
            nome_var = ident_token.getText()
            line = self.linha_token(ident_token.getSymbol())
            
            # Tenta declarar o símbolo no escopo atual.
            if not self.symbol_table.declare_symbol(nome_var, 'variavel', declared_type_info, line):
                self.erros.append(f"Linha {line}: identificador {nome_var} ja declarado anteriormente")

    # Verifica a atribuição.
    def enterAtribuicao(self, ctx:LAParser.AtribuicaoContext):
        # A regra de atribuição é: (IDENT | acesso_campo | CIRCUNFLEXO IDENT) ATRIBUICAO expressao
        # O LHS pode ser o primeiro filho. Precisamos determinar o tipo desse primeiro filho.
        lvalue_node = ctx.getChild(0)
        lvalue_type = None
        line = self.linha_token(ctx.start) # Linha do início da atribuição

        if isinstance(lvalue_node, TerminalNode) and lvalue_node.getSymbol().type == LAParser.IDENT:
            # Caso 1: IDENT simples
            lvalue_type = self.resolve_lvalue_type(lvalue_node)
            line = self.linha_token(lvalue_node.getSymbol())
        elif isinstance(lvalue_node, LAParser.Acesso_campoContext):
            # Caso 2: Acesso a campo
            lvalue_type = self.resolve_lvalue_type(lvalue_node)
            line = self.linha_token(lvalue_node.start)
        elif isinstance(lvalue_node, TerminalNode) and lvalue_node.getSymbol().type == LAParser.CIRCUNFLEXO:
            # Caso 3: Desreferenciação de ponteiro (^IDENT)
            # O próximo filho deve ser o IDENT.
            ident_node = ctx.getChild(1) # O IDENT após o CIRCUNFLEXO
            if isinstance(ident_node, TerminalNode) and ident_node.getSymbol().type == LAParser.IDENT:
                name = ident_node.getText()
                sym_entry = self.symbol_table.lookup_symbol(name)
                if sym_entry is None:
                    self.erros.append(f"Linha {self.linha_token(ident_node.getSymbol())}: identificador {name} nao declarado")
                    return # Sai, pois o lvalue é inválido
                
                # Verifica se o tipo da entrada é uma string e se começa com '^'
                if not (isinstance(sym_entry.type_info, str) and sym_entry.type_info.startswith('^')):
                    self.erros.append(f"Linha {self.linha_token(lvalue_node.getSymbol())}: identificador {name} nao eh um ponteiro para ser desreferenciado")
                    return # Sai, pois o lvalue é inválido
                
                lvalue_type = sym_entry.type_info[1:] # Tipo base do ponteiro
                line = self.linha_token(lvalue_node.getSymbol()) # Linha do circunflexo
            else:
                self.erros.append(f"Linha {self.linha_token(lvalue_node.getSymbol())}: expressao invalida apos '^'")
                return # Sai

        if lvalue_type is None: # Se um erro já foi relatado pelo l-value, apenas retorna.
            return

        # Resolve o tipo da expressão no lado direito (R-value).
        rvalue_type = self.tipo_expressao(ctx.expressao())

        if rvalue_type is None: # Se um erro já foi relatado pela expressão, apenas retorna.
            return

        # Compara os tipos usando a função de compatibilidade aprimorada.
        if not self.eh_compativel_atribuicao(lvalue_type, rvalue_type):
            # Para a mensagem de erro, tente reconstruir o texto do l-value
            lvalue_text = ""
            if isinstance(lvalue_node, TerminalNode):
                lvalue_text = lvalue_node.getText()
                if lvalue_node.getSymbol().type == LAParser.CIRCUNFLEXO:
                    lvalue_text += ctx.getChild(1).getText()
            elif isinstance(lvalue_node, LAParser.Acesso_campoContext):
                lvalue_text = lvalue_node.getText()


            self.erros.append(f"Linha {line}: atribuicao nao compativel para {lvalue_text}")

    # Verifica identificadores usados no comando 'leia'.
    def enterLeitura(self, ctx:LAParser.LeituraContext):
        if ctx.lista_identificadores():
            # A regra 'lista_identificadores' é: (IDENT | acesso_campo) (',' (IDENT | acesso_campo))*
            # Itera sobre os filhos para encontrar IDENT ou acesso_campo
            for child in ctx.lista_identificadores().children:
                if isinstance(child, TerminalNode) and child.getSymbol().type == LAParser.VIRG:
                    continue # Ignora as vírgulas

                # Determina o tipo do identificador usando resolve_lvalue_type
                # Este método já reporta erros se o identificador não for declarado
                self.resolve_lvalue_type(child) 
        
    # Verifica expressões usadas no comando 'escreva'.
    def enterEscrita(self, ctx:LAParser.EscritaContext):
        for exp_ctx in ctx.expressao():
            # Apenas resolve o tipo da expressão; 'tipo_expressao' já reporta erros internamente.
            self.tipo_expressao(exp_ctx)

    # Verifica a condição no comando 'enquanto'.
    def enterComandoenquanto(self, ctx:LAParser.ComandoenquantoContext):
        cond_type = self.tipo_expressao(ctx.expressao())
        if cond_type is not None and cond_type != 'logico':
            self.erros.append(f"Linha {self.linha_token(ctx.expressao().start)}: condicao do comando 'enquanto' nao eh do tipo logico. Encontrado '{cond_type}'")

    # Verifica a condição no comando 'se'.
    def enterComandose(self, ctx:LAParser.ComandoseContext):
        cond_type = self.tipo_expressao(ctx.expressao())
        if cond_type is not None and cond_type != 'logico':
            self.erros.append(f"Linha {self.linha_token(ctx.expressao().start)}: condicao do comando 'se' nao eh do tipo logico. Encontrado '{cond_type}'")

    # Verifica o comando 'retorne'.
    def enterRetorne(self, ctx:LAParser.RetorneContext):
        # 'retorne' só é permitido dentro de funções.
        # Verifica se estamos em um escopo de função (onde 'current_function_return_type' é definido).
        if self.in_function_or_procedure == 0 or self.current_function_return_type is None:
            self.erros.append(f"Linha {self.linha_token(ctx.start)}: comando retorne nao permitido neste escopo")
            return

        # Se há uma expressão após 'retorne', verifica sua compatibilidade com o tipo de retorno da função.
        if ctx.expressao():
            return_exp_type = self.tipo_expressao(ctx.expressao())
            if return_exp_type is None: return # Se a expressão já tem um erro, apenas retorna.

            if not self.eh_compativel_atribuicao(self.current_function_return_type, return_exp_type):
                self.erros.append(f"Linha {self.linha_token(ctx.start)}: tipo de retorno incompativel. Esperado '{self.current_function_return_type}', encontrado '{return_exp_type}'")
        else:
            # Se 'retorne' é usado sem expressao, mas a função espera um tipo de retorno (não 'void').
            # Assume-se que funções LA sempre retornam um tipo e não podem ser 'void' no sentido de C.
            # Se o tipo de retorno esperado não é "void" (ou equivalente para "nada"), então é um erro.
            if self.current_function_return_type != 'void': # 'void' é um marcador interno para procedimentos
                self.erros.append(f"Linha {self.linha_token(ctx.start)}: comando retorne sem expressao em funcao que espera um retorno")

    # Obtém o tipo de retorno de uma chamada de função e verifica a compatibilidade dos argumentos.
    def tipo_funcao(self, ctx:LAParser.Chamada_funcaoContext):
        nome_func = ctx.IDENT().getText()
        line = self.linha_token(ctx.IDENT().getSymbol())
        
        # Busca a informação da função na tabela de símbolos.
        func_info_entry = self.symbol_table.lookup_symbol(nome_func)
        if func_info_entry == None: 
            self.erros.append(f"Linha {line}: identificador {nome_func} nao declarado")
            return None # Não é possível determinar o tipo se a função não foi declarada.
        
        # Verifica se o identificador encontrado é realmente uma função.
        if func_info_entry.category != 'funcao':
            self.erros.append(f"Linha {line}: identificador {nome_func} nao eh uma funcao")
            return None

        # Obtém os parâmetros esperados e os argumentos reais.
        expected_params = func_info_entry.type_info['parametros']
        actual_args = []
        if ctx.lista_expressao(): # Verifica se há argumentos na chamada.
            actual_args = [self.tipo_expressao(exp) for exp in ctx.lista_expressao().expressao()]
            actual_args = [arg_type for arg_type in actual_args if arg_type is not None] # Filtra argumentos com erros

        # Verifica o número de argumentos.
        if len(expected_params) != len(actual_args):
            self.erros.append(f"Linha {line}: incompatibilidade de argumentos na chamada de {nome_func} (numero de argumentos)")
            return None

        # Verifica a compatibilidade de tipo de cada argumento.
        for i, expected_type in enumerate(expected_params):
            if not self.eh_compativel_atribuicao(expected_type, actual_args[i]):
                self.erros.append(f"Linha {line}: incompatibilidade de argumentos na chamada de {nome_func} (tipo do argumento {i+1})")
                return None # Se um argumento é incompatível, toda a chamada é inválida.
        
        return func_info_entry.type_info['retorno'] # Retorna o tipo de retorno da função.


# Função principal para executar o analisador semântico.
def main():
    if len(sys.argv) != 3:
        print("Uso: python3 analisador_semantico.py entrada.txt saida.txt")
        sys.exit(1)

    arquivo_entrada = sys.argv[1]
    arquivo_saida = sys.argv[2]

    try:
        input_stream = FileStream(arquivo_entrada, encoding='utf-8')
        lexer = LALexer(input_stream)
        # Remove o listener de erro padrão para evitar saída de erros de sintaxe no console.
        lexer.removeErrorListeners()
        # Opcional: Adicione um CustomErrorListener se desejar capturar e manipular erros de sintaxe.
        # lexer.addErrorListener(CustomErrorListener())

        token_stream = CommonTokenStream(lexer)
        parser = LAParser(token_stream)
        parser.removeErrorListeners() # Remove o listener de erro padrão do parser também.
        # parser.addErrorListener(CustomErrorListener())

        tree = parser.programa() # Inicia a análise a partir da regra 'programa'.

        analisador = AnalisadorSemantico(token_stream)
        walker = ParseTreeWalker()
        walker.walk(analisador, tree) # Percorre a árvore de parse com o analisador.

        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            for erro in analisador.erros:
                f.write(erro + '\n')
            f.write("Fim da compilacao\n")

    except FileNotFoundError:
        print(f"Erro: Arquivo de entrada '{arquivo_entrada}' nao encontrado.")
        sys.exit(1)
    except Exception as e:
        print(f"Ocorreu um erro inesperado durante a análise: {e}")
        # Opcional: Printar traceback para depuração
        # import traceback
        # traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
