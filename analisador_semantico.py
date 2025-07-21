import sys
from antlr4 import *
from LAParser import LAParser
from LALexer import LALexer
from LAListener import LAListener

# Lista de tipos válidos (de acordo com a gramática)
TIPOS_VALIDOS = {'literal', 'inteiro', 'real', 'logico'}

class AnalisadorSemantico(LAListener):
    def __init__(self, token_stream):
        self.simbolos = {}   # dicionário nome -> tipo
        self.erros = []
        self.tokens = token_stream
        self.tipos_definidos = {}  # Para armazenar tipos personalizados como registros
        self.campos_registro = {}  # Para armazenar campos de registros
        self.funcoes = {}  # Para armazenar informações sobre funções: nome -> {'tipo_retorno': str, 'parametros': [(nome, tipo)]}
        self.procedimentos = {}  # Para armazenar informações sobre procedimentos
        self.escopo_atual = 'global'  # Para controlar escopo (global, funcao, procedimento)
        self.simbolos_locais = {}  # Para armazenar símbolos do escopo local atual
        self.constantes = {}  # Para armazenar constantes declaradas

    # Pega o número da linha do token (para mensagens)
    def linha_token(self, token):
        return token.line

    def tipo_expressao(self, ctx):
        # Importa as classes do parser para usar isinstance
        from LAParser import LAParser

        # 1) Caso raiz: expressao : expressao_logica
        if isinstance(ctx, LAParser.ExpressaoContext):
            return self.tipo_expressao(ctx.expressao_logica())

        # 2) expressao_logica : expressao_relacional ('e' expressao_relacional | 'ou' expressao_relacional)*
        elif isinstance(ctx, LAParser.Expressao_logicaContext):
            # Avalia o tipo de todas as expressao_relacional dentro da expressão lógica
            tipos = [self.tipo_expressao(child) for child in ctx.expressao_relacional()]
            
            # Se só um elemento (sem operadores lógicos)
            if len(tipos) == 1:
                return tipos[0]
            
            # Senão, todos precisam ser 'logico' para o 'e' / 'ou' fazer sentido
            if all(t == 'logico' for t in tipos):
                return 'logico'
            else:
                return None

        # 3) expressao_relacional : expressao_aritmetica ((OP_RELACIONAL | IGUAL) expressao_aritmetica)?
        elif isinstance(ctx, LAParser.Expressao_relacionalContext):
            if ctx.getChildCount() == 1:
                # Só expressao_aritmetica, sem operador relacional
                return self.tipo_expressao(ctx.expressao_aritmetica(0))
            else:
                tipo_esq = self.tipo_expressao(ctx.expressao_aritmetica(0))
                tipo_dir = self.tipo_expressao(ctx.expressao_aritmetica(1))
                # Operadores relacionais retornam 'logico' se os tipos são compatíveis (ex: inteiros, reais)
                if tipo_esq in ('inteiro','real') and tipo_dir in ('inteiro','real'):
                    return 'logico'
                if tipo_esq == tipo_dir:
                    return 'logico'
                return None

        # 4) expressao_aritmetica : termo (( '+' | '-' ) termo)*
        elif isinstance(ctx, LAParser.Expressao_aritmeticaContext):
            tipos = [self.tipo_expressao(term) for term in ctx.termo()]
            tipo_acumulado = tipos[0]
            for t in tipos[1:]:
                if tipo_acumulado in ('inteiro','real') and t in ('inteiro','real'):
                    # promoção numérica
                    tipo_acumulado = 'real' if 'real' in (tipo_acumulado, t) else 'inteiro'
                elif tipo_acumulado == 'literal' and t == 'literal':
                    # concatenação literal
                    tipo_acumulado = 'literal'
                else:
                    return None
            return tipo_acumulado

        # 5) termo : fator (( '*' | '/' | '%' ) fator)*
        elif isinstance(ctx, LAParser.TermoContext):
            tipos = [self.tipo_expressao(fat) for fat in ctx.fator()]
            tipo_acumulado = tipos[0]
            for t in tipos[1:]:
                if tipo_acumulado in ('inteiro','real') and t in ('inteiro','real'):
                    tipo_acumulado = 'real' if 'real' in (tipo_acumulado, t) else 'inteiro'
                else:
                    return None
            return tipo_acumulado

        # 6) fator : vários casos terminais e recursivos
        elif isinstance(ctx, LAParser.FatorContext):
            # Identificador
            if ctx.IDENT():
                nome = ctx.IDENT().getText()
                # Verificar primeiro no escopo local, depois no global
                tipo_var = self.simbolos_locais.get(nome) or self.simbolos.get(nome)
                if tipo_var is None:
                    self.erros.append(f"Linha {ctx.start.line}: identificador {nome} nao declarado")
                    return None
                return tipo_var

            # Constantes numéricas
            if ctx.NUM_INT():
                return 'inteiro'
            if ctx.NUM_REAL():
                return 'real'

            # Literal cadeia
            if ctx.CADEIA():
                return 'literal'

            # Verdadeiro ou falso (booleano)
            if ctx.getText() in ('verdadeiro', 'falso'):
                return 'logico'

            # Parênteses: desce para a expressao interna
            if ctx.ABREPAR():
                return self.tipo_expressao(ctx.expressao())

            # Negação unária (- fator)
            if ctx.getChildCount() == 2 and ctx.getChild(0).getText() == '-':
                return self.tipo_expressao(ctx.fator())

            # Negação lógica (nao fator)
            if ctx.getChildCount() == 2 and ctx.getChild(0).getText().lower() == 'nao':
                t = self.tipo_expressao(ctx.fator())
                return 'logico' if t == 'logico' else None

            # Endereçamento (& IDENT ou acesso_campo)
            if ctx.getChildCount() == 2 and ctx.getChild(0).getText() == '&':
                # Endereço: aceita qualquer tipo, retorna 'endereco' ou None conforme sua definição
                return 'endereco'

            # Potência (CIRCUNFLEXO IDENT)
            if ctx.CIRCUNFLEXO():
                # Depende da declaração da variável
                nome = ctx.IDENT().getText()
                return self.simbolos.get(nome)

            # chamada_funcao (implemente se necessário)
            if ctx.chamada_funcao():
                # Deve retornar o tipo do resultado da função
                return self.tipo_funcao(ctx.chamada_funcao())

            # acesso_campo (implemente se necessário)
            if ctx.acesso_campo():
                return self.tipo_acesso_campo(ctx.acesso_campo())

            # acesso_array (implementar suporte para arrays)
            if hasattr(ctx, 'acesso_array') and ctx.acesso_array():
                return self.tipo_acesso_array(ctx.acesso_array())

            # Se não reconhecer, retorna None
            return None

        else:
            # Contexto não tratado
            return None

        # Adicionar suporte para acesso_campo diretamente
        if isinstance(ctx, LAParser.Acesso_campoContext):
            return self.tipo_acesso_campo(ctx)
        
        # Adicionar suporte para acesso_array diretamente
        if hasattr(LAParser, 'Acesso_arrayContext') and isinstance(ctx, LAParser.Acesso_arrayContext):
            return self.tipo_acesso_array(ctx)

    def tipo_acesso_campo(self, ctx):
        """Determina o tipo de um acesso a campo como variavel.campo"""
        if hasattr(ctx, 'IDENT') and ctx.IDENT():
            nome_var = ctx.IDENT(0).getText()
            nome_campo = ctx.IDENT(1).getText()
            
            # Verificar se a variável existe (primeiro local, depois global)
            if nome_var not in self.simbolos_locais and nome_var not in self.simbolos:
                self.erros.append(f"Linha {ctx.start.line}: identificador {nome_var}.{nome_campo} nao declarado")
                return None
            
            # Verificar se a variável tem campos (é um registro)
            if nome_var in self.campos_registro:
                campos = self.campos_registro[nome_var]
                if nome_campo in campos:
                    return campos[nome_campo]
                else:
                    self.erros.append(f"Linha {ctx.start.line}: identificador {nome_var}.{nome_campo} nao declarado")
                    return None
            else:
                # Variável não é um registro
                self.erros.append(f"Linha {ctx.start.line}: identificador {nome_var}.{nome_campo} nao declarado")
                return None
        return None

    def tipo_acesso_array(self, ctx):
        """Determina o tipo de um acesso a array como variavel[indice]"""
        if hasattr(ctx, 'IDENT') and ctx.IDENT():
            nome_var = ctx.IDENT().getText()
            
            # Verificar se a variável existe
            if nome_var not in self.simbolos:
                self.erros.append(f"Linha {ctx.start.line}: identificador {nome_var} nao declarado")
                return None
            
            # Verificar se o índice é um inteiro
            tipo_indice = self.tipo_expressao(ctx.expressao())
            if tipo_indice != 'inteiro':
                # Não reportar erro aqui, apenas retornar None para indicar problema
                pass
            
            # Retornar o tipo base do array (assumindo que arrays são do mesmo tipo dos elementos)
            return self.simbolos_locais.get(nome_var) or self.simbolos.get(nome_var)
        return None

    def tipo_funcao(self, ctx):
        """Determina o tipo de retorno de uma chamada de função e valida parâmetros"""
        if hasattr(ctx, 'IDENT') and ctx.IDENT():
            nome_funcao = ctx.IDENT().getText()
            
            # Verificar se a função existe
            if nome_funcao not in self.funcoes:
                self.erros.append(f"Linha {ctx.start.line}: identificador {nome_funcao} nao declarado")
                return None
            
            # Obter informações da função
            info_funcao = self.funcoes[nome_funcao]
            parametros_esperados = info_funcao['parametros']
            
            # Verificar parâmetros passados
            parametros_passados = []
            if ctx.lista_expressao():
                for exp in ctx.lista_expressao().expressao():
                    tipo_param = self.tipo_expressao(exp)
                    parametros_passados.append(tipo_param)
            
            # Validar número de parâmetros
            if len(parametros_passados) != len(parametros_esperados):
                self.erros.append(f"Linha {ctx.start.line}: incompatibilidade de parametros na chamada de {nome_funcao}")
                return info_funcao['tipo_retorno']
            
            # Validar tipos dos parâmetros
            for i, (tipo_passado, (_, tipo_esperado)) in enumerate(zip(parametros_passados, parametros_esperados)):
                if tipo_passado and tipo_passado != tipo_esperado:  # Exigir compatibilidade exata para parâmetros
                    self.erros.append(f"Linha {ctx.start.line}: incompatibilidade de parametros na chamada de {nome_funcao}")
                    break
            
            return info_funcao['tipo_retorno']
        return None

    
    def eh_compatível(self, tipo_var, tipo_exp):
        if tipo_var == tipo_exp:
            return True
        # Permitir atribuir inteiro para real
        if tipo_var == 'real' and tipo_exp == 'inteiro':
            return True
        return False

    def enterAtribuicao(self, ctx:LAParser.AtribuicaoContext):
        # Identificar o lado esquerdo da atribuição
        lado_esquerdo = ctx.getChild(0)
        lado_esquerdo_texto = lado_esquerdo.getText()
        
        # Debug: print info about the left side
        # print(f"Debug: lado_esquerdo_texto = '{lado_esquerdo_texto}'")
        # print(f"Debug: lado_esquerdo type = {type(lado_esquerdo)}")
        # print(f"Debug: lado_esquerdo children = {lado_esquerdo.getChildCount()}")
        
        # Verificar se é um ponteiro (^IDENT) - o primeiro filho é ^ e o segundo é IDENT
        if lado_esquerdo_texto == '^':
            # É um ponteiro dereference: ^ponteiro
            # O identificador do ponteiro está no segundo filho
            ident_node = ctx.getChild(1)
            nome_ponteiro = ident_node.getText()
            tipo_ponteiro = self.simbolos_locais.get(nome_ponteiro) or self.simbolos.get(nome_ponteiro)
            nome_var = f"^{nome_ponteiro}"  # ^ponteiro
            token_var = ident_node.getSymbol()
            
            if tipo_ponteiro is None:
                # Ponteiro não declarado
                self.erros.append(f"Linha {token_var.line}: identificador {nome_ponteiro} nao declarado")
                return  # Sair cedo se ponteiro não declarado
            else:
                # O tipo da variável apontada é o tipo do ponteiro
                tipo_var = tipo_ponteiro
        elif hasattr(lado_esquerdo, 'getSymbol'):  # É um terminal (IDENT)
            nome_var = lado_esquerdo.getText()
            tipo_var = self.simbolos_locais.get(nome_var) or self.simbolos.get(nome_var)
            token_var = lado_esquerdo.getSymbol()
            
            if tipo_var is None:
                self.erros.append(f"Linha {token_var.line}: identificador {nome_var} nao declarado")
                return
        elif hasattr(lado_esquerdo, 'IDENT') and lado_esquerdo.IDENT():  # É acesso_campo ou acesso_array
            nome_var = lado_esquerdo.getText()
            
            # Verificar se é acesso a array (tem colchetes)
            if hasattr(lado_esquerdo, 'ABRE_COLCHETE'):
                # É acesso a array
                tipo_var = self.tipo_acesso_array(lado_esquerdo)
                token_var = lado_esquerdo.IDENT().getSymbol()
            else:
                # É acesso a campo
                tipo_var = self.tipo_acesso_campo(lado_esquerdo)
                token_var = lado_esquerdo.IDENT(0).getSymbol()
            
            # Se tipo_var é None, o erro já foi reportado nos métodos específicos
            if tipo_var is None:
                return
        else:
            # Caso não identificado
            nome_var = lado_esquerdo.getText()
            tipo_var = None
            token_var = ctx.start
            self.erros.append(f"Linha {token_var.line}: identificador {nome_var} nao declarado")
            return

        # Verificar tipo da expressão do lado direito
        tipo_exp = self.tipo_expressao(ctx.expressao())

        # Comparar tipos (apenas se ambos os tipos forem conhecidos)
        if tipo_var is not None and tipo_exp is not None and not self.eh_compatível(tipo_var, tipo_exp):
            if hasattr(token_var, 'line'):
                linha = token_var.line
            else:
                linha = ctx.start.line
            self.erros.append(f"Linha {linha}: atribuicao nao compativel para {nome_var}")

    # Captura variáveis declaradas na regra "declaracao"
    def enterDeclaracoes_locais(self, ctx:LAParser.Declaracoes_locaisContext):
        # Process each 'declare lista_variaveis' inside the declaracoes_locais
        # According to the grammar: declaracoes_locais : ('declare' lista_variaveis)+
        
        # Get all lista_variaveis children
        if hasattr(ctx, 'lista_variaveis'):
            for lista_vars in ctx.lista_variaveis():
                self.process_lista_variaveis(lista_vars)

    def extract_variable_names(self, var_ctx):
        """Extract only the variable names from a variavel context, ignoring array size expressions"""
        variable_names = []
        
        # The grammar is: IDENT (ABRE_COLCHETE (NUM_INT | IDENT) FECHA_COLCHETE)? (',' IDENT (ABRE_COLCHETE (NUM_INT | IDENT) FECHA_COLCHETE)?)* ':' tipo
        # We need to identify which IDENT tokens are variable names vs array sizes
        
        # Parse the children to identify the structure
        children = [var_ctx.getChild(i) for i in range(var_ctx.getChildCount())]
        
        i = 0
        while i < len(children):
            child = children[i]
            
            # Look for IDENT tokens
            if hasattr(child, 'getSymbol') and child.getSymbol().type == LALexer.IDENT:
                # This is a variable name
                variable_names.append(child.getText())
                
                # Skip over potential array bracket section
                if i + 1 < len(children) and hasattr(children[i + 1], 'getSymbol') and children[i + 1].getSymbol().type == LALexer.ABRE_COLCHETE:
                    # Skip [, array_size, ]
                    i += 3  # Skip ABRE_COLCHETE, array_size, FECHA_COLCHETE
                else:
                    i += 1
            elif hasattr(child, 'getText') and child.getText() == ',':
                # Skip comma
                i += 1
            else:
                # Skip other tokens like ':'
                i += 1
                
        return variable_names

    def process_lista_variaveis(self, lista_vars_ctx):
        """Helper method to process lista_variaveis in any context"""
        for var_ctx in lista_vars_ctx.variavel():
            self.process_variavel(var_ctx)

    def process_variavel(self, var_ctx):
        """Helper method to process a single variavel declaration"""
        tipo_ctx = var_ctx.tipo()
        
        # Verificar se tipo_ctx não é None
        if tipo_ctx is None:
            return
        
        # Verificar se é um tipo registro
        if hasattr(tipo_ctx, 'tipo_registro') and tipo_ctx.tipo_registro():
            # É um tipo registro - processar campos
            registro_ctx = tipo_ctx.tipo_registro()
            tipo_texto = 'registro'
            
            # Armazenar campos do registro para cada variável
            campos = {}
            for campo_ctx in registro_ctx.lista_campos().campo():
                tipo_campo = campo_ctx.tipo_base().getText().replace("^", "")
                if tipo_campo not in TIPOS_VALIDOS:
                    token_tipo = campo_ctx.tipo_base().start
                    self.erros.append(f"Linha {self.linha_token(token_tipo)}: tipo {tipo_campo} nao declarado")
                
                # Adicionar todos os identificadores do campo
                for j in range(campo_ctx.IDENT().__len__()):
                    nome_campo = campo_ctx.IDENT(j).getText()
                    campos[nome_campo] = tipo_campo
            
            # Registrar cada variável do tipo registro
            for i in range(var_ctx.IDENT().__len__()):
                nome_var = var_ctx.IDENT(i).getText()
                # Verificar conflitos baseado no escopo atual
                conflict_found = False
                if self.escopo_atual in ['funcao', 'procedimento']:
                    if nome_var in self.simbolos_locais or nome_var in self.simbolos:
                        conflict_found = True
                else:
                    if nome_var in self.simbolos:
                        conflict_found = True
                
                if conflict_found:
                    token_var = var_ctx.IDENT(i).getSymbol()
                    self.erros.append(f"Linha {self.linha_token(token_var)}: identificador {nome_var} ja declarado anteriormente")
                else:
                    # Escolher o escopo correto
                    if self.escopo_atual in ['funcao', 'procedimento']:
                        self.simbolos_locais[nome_var] = tipo_texto
                    else:
                        self.simbolos[nome_var] = tipo_texto
                    self.campos_registro[nome_var] = campos
        else:
            # Tipo simples, ponteiro, ou tipo definido pelo usuário
            if hasattr(tipo_ctx, 'tipo_base') and tipo_ctx.tipo_base():
                tipo_texto = tipo_ctx.tipo_base().getText().replace("^", "")
            elif hasattr(tipo_ctx, 'tipo_identificado') and tipo_ctx.tipo_identificado():
                tipo_texto = tipo_ctx.tipo_identificado().getText().replace("^", "")
            else:
                tipo_texto = tipo_ctx.getText().replace("^", "")
            
            # Verificar se é um tipo válido (primitivo ou definido pelo usuário)
            if tipo_texto not in TIPOS_VALIDOS and tipo_texto not in self.tipos_definidos:
                token_tipo = tipo_ctx.start
                self.erros.append(f"Linha {self.linha_token(token_tipo)}: tipo {tipo_texto} nao declarado")
            
            # Registrar cada variável
            for i in range(var_ctx.IDENT().__len__()):
                nome_var = var_ctx.IDENT(i).getText()
                # Verificar conflito com variáveis já declaradas, tipos, funções ou procedimentos
                # Mas ignore conflitos com constantes (elas podem ser usadas em tamanhos de array)
                conflict_found = False
                
                # Verificar no escopo atual
                if self.escopo_atual in ['funcao', 'procedimento']:
                    # Em escopo local, verificar conflitos locais e globais
                    if ((nome_var in self.simbolos_locais) or 
                        (nome_var in self.simbolos) or 
                        nome_var in self.tipos_definidos or 
                        nome_var in self.funcoes or 
                        nome_var in self.procedimentos or
                        nome_var in self.constantes):
                        conflict_found = True
                else:
                    # Em escopo global, verificar apenas conflitos globais
                    if ((nome_var in self.simbolos) or 
                        nome_var in self.tipos_definidos or 
                        nome_var in self.funcoes or 
                        nome_var in self.procedimentos or
                        nome_var in self.constantes):
                        conflict_found = True
                
                if conflict_found:
                    # Find the correct token for the variable name
                    token_var = None
                    for j in range(var_ctx.IDENT().__len__()):
                        if var_ctx.IDENT(j).getText() == nome_var:
                            token_var = var_ctx.IDENT(j).getSymbol()
                            break
                    if token_var:
                        self.erros.append(f"Linha {self.linha_token(token_var)}: identificador {nome_var} ja declarado anteriormente")
                elif nome_var not in self.constantes:  # Só declare como variável se não for uma constante
                    # Escolher o escopo correto baseado no escopo atual
                    if self.escopo_atual in ['funcao', 'procedimento']:
                        self.simbolos_locais[nome_var] = tipo_texto
                    else:
                        self.simbolos[nome_var] = tipo_texto
                    # Se for um tipo registro definido pelo usuário, copiar seus campos
                    if tipo_texto in self.tipos_definidos and tipo_texto in self.campos_registro:
                        self.campos_registro[nome_var] = self.campos_registro[tipo_texto]

    def enterDeclaracao(self, ctx:LAParser.DeclaracaoContext):
        for var_ctx in ctx.lista_variaveis().variavel():
            tipo_ctx = var_ctx.tipo()
            
            # Verificar se tipo_ctx não é None
            if tipo_ctx is None:
                continue
            
            # Verificar se é um tipo registro
            if hasattr(tipo_ctx, 'tipo_registro') and tipo_ctx.tipo_registro():
                # É um tipo registro - processar campos
                registro_ctx = tipo_ctx.tipo_registro()
                tipo_texto = 'registro'
                
                # Armazenar campos do registro para cada variável
                campos = {}
                for campo_ctx in registro_ctx.lista_campos().campo():
                    tipo_campo = campo_ctx.tipo_base().getText().replace("^", "")
                    if tipo_campo not in TIPOS_VALIDOS:
                        token_tipo = campo_ctx.tipo_base().start
                        self.erros.append(f"Linha {self.linha_token(token_tipo)}: tipo {tipo_campo} nao declarado")
                    
                    # Adicionar todos os identificadores do campo
                    for j in range(campo_ctx.IDENT().__len__()):
                        nome_campo = campo_ctx.IDENT(j).getText()
                        campos[nome_campo] = tipo_campo
                
                # Registrar cada variável do tipo registro
                for i in range(var_ctx.IDENT().__len__()):
                    nome_var = var_ctx.IDENT(i).getText()
                    # Verificar conflitos baseado no escopo atual
                    conflict_found = False
                    if self.escopo_atual in ['funcao', 'procedimento']:
                        if nome_var in self.simbolos_locais or nome_var in self.simbolos:
                            conflict_found = True
                    else:
                        if nome_var in self.simbolos:
                            conflict_found = True
                    
                    if conflict_found:
                        token_var = var_ctx.IDENT(i).getSymbol()
                        self.erros.append(f"Linha {self.linha_token(token_var)}: identificador {nome_var} ja declarado anteriormente")
                    else:
                        # Escolher o escopo correto
                        if self.escopo_atual in ['funcao', 'procedimento']:
                            self.simbolos_locais[nome_var] = tipo_texto
                        else:
                            self.simbolos[nome_var] = tipo_texto
                        self.campos_registro[nome_var] = campos
            else:
                # Tipo simples, ponteiro, ou tipo definido pelo usuário
                if hasattr(tipo_ctx, 'tipo_base') and tipo_ctx.tipo_base():
                    tipo_texto = tipo_ctx.tipo_base().getText().replace("^", "")
                elif hasattr(tipo_ctx, 'tipo_identificado') and tipo_ctx.tipo_identificado():
                    tipo_texto = tipo_ctx.tipo_identificado().getText().replace("^", "")
                else:
                    tipo_texto = tipo_ctx.getText().replace("^", "")
                
                # Verificar se é um tipo válido (primitivo ou definido pelo usuário)
                if tipo_texto not in TIPOS_VALIDOS and tipo_texto not in self.tipos_definidos:
                    token_tipo = tipo_ctx.start
                    self.erros.append(f"Linha {self.linha_token(token_tipo)}: tipo {tipo_texto} nao declarado")
                
                # Registrar cada variável
                # Need to carefully parse the variable structure to distinguish between
                # variable names and array size expressions
                var_names = self.extract_variable_names(var_ctx)
                
                for nome_var in var_names:
                    # Verificar conflito com variáveis já declaradas, tipos, funções ou procedimentos
                    # Mas ignore conflitos com constantes (elas podem ser usadas em tamanhos de array)
                    conflict_found = False
                    
                    # Verificar no escopo atual
                    if self.escopo_atual in ['funcao', 'procedimento']:
                        # Em escopo local, verificar conflitos locais e globais
                        if ((nome_var in self.simbolos_locais) or 
                            (nome_var in self.simbolos) or 
                            nome_var in self.tipos_definidos or 
                            nome_var in self.funcoes or 
                            nome_var in self.procedimentos or
                            nome_var in self.constantes):
                            conflict_found = True
                    else:
                        # Em escopo global, verificar apenas conflitos globais
                        if ((nome_var in self.simbolos) or 
                            nome_var in self.tipos_definidos or 
                            nome_var in self.funcoes or 
                            nome_var in self.procedimentos or
                            nome_var in self.constantes):
                            conflict_found = True
                    
                    if conflict_found:
                        # Find the correct token for the variable name
                        token_var = None
                        for j in range(var_ctx.IDENT().__len__()):
                            if var_ctx.IDENT(j).getText() == nome_var:
                                token_var = var_ctx.IDENT(j).getSymbol()
                                break
                        if token_var:
                            self.erros.append(f"Linha {self.linha_token(token_var)}: identificador {nome_var} ja declarado anteriormente")
                    elif nome_var not in self.constantes:  # Só declare como variável se não for uma constante
                        # Escolher o escopo correto baseado no escopo atual
                        if self.escopo_atual in ['funcao', 'procedimento']:
                            self.simbolos_locais[nome_var] = tipo_texto
                        else:
                            self.simbolos[nome_var] = tipo_texto
                        # Se for um tipo registro definido pelo usuário, copiar seus campos
                        if tipo_texto in self.tipos_definidos and tipo_texto in self.campos_registro:
                            self.campos_registro[nome_var] = self.campos_registro[tipo_texto]

    # Captura tipos definidos na regra "declaracao_tipo"
    def enterDeclaracao_tipo(self, ctx:LAParser.Declaracao_tipoContext):
        nome_tipo = ctx.IDENT().getText()
        
        # Verificar se o tipo já foi declarado
        if nome_tipo in self.tipos_definidos or nome_tipo in self.simbolos:
            token_tipo = ctx.IDENT().getSymbol()
            self.erros.append(f"Linha {self.linha_token(token_tipo)}: identificador {nome_tipo} ja declarado anteriormente")
        else:
            # Registrar o tipo
            self.tipos_definidos[nome_tipo] = 'tipo_personalizado'
            
            # Se for um tipo registro, processar seus campos
            if hasattr(ctx, 'tipo_registro') and ctx.tipo_registro():
                campos = {}
                registro_ctx = ctx.tipo_registro()
                for campo_ctx in registro_ctx.lista_campos().campo():
                    tipo_campo = campo_ctx.tipo_base().getText().replace("^", "")
                    if tipo_campo not in TIPOS_VALIDOS:
                        token_tipo = campo_ctx.tipo_base().start
                        self.erros.append(f"Linha {self.linha_token(token_tipo)}: tipo {tipo_campo} nao declarado")
                    
                    # Adicionar todos os identificadores do campo
                    for j in range(campo_ctx.IDENT().__len__()):
                        nome_campo = campo_ctx.IDENT(j).getText()
                        campos[nome_campo] = tipo_campo
                
                # Armazenar os campos do tipo
                self.campos_registro[nome_tipo] = campos

    def enterDeclaracao_constante(self, ctx:LAParser.Declaracao_constanteContext):
        nome_constante = ctx.IDENT().getText()
        tipo_constante = ctx.tipo_base().getText().replace("^", "")
        
        # Verificar se a constante já foi declarada
        if nome_constante in self.constantes or nome_constante in self.simbolos or nome_constante in self.tipos_definidos:
            token_const = ctx.IDENT().getSymbol()
            self.erros.append(f"Linha {self.linha_token(token_const)}: identificador {nome_constante} ja declarado anteriormente")
        else:
            # Registrar a constante
            self.constantes[nome_constante] = tipo_constante
            # Também adicionar ao símbolos para poder ser usada em expressões
            self.simbolos[nome_constante] = tipo_constante

    def enterDeclaracao_funcao(self, ctx:LAParser.Declaracao_funcaoContext):
        nome_funcao = ctx.IDENT().getText()
        tipo_retorno = ctx.tipo_base().getText().replace("^", "")
        
        # Verificar se a função já foi declarada
        if nome_funcao in self.funcoes or nome_funcao in self.procedimentos or nome_funcao in self.simbolos:
            token_funcao = ctx.IDENT().getSymbol()
            self.erros.append(f"Linha {self.linha_token(token_funcao)}: identificador {nome_funcao} ja declarado anteriormente")
        else:
            # Extrair parâmetros
            parametros = []
            if ctx.parametros():
                for param_ctx in ctx.parametros().parametro():
                    nome_param = param_ctx.IDENT().getText()
                    if param_ctx.tipo_base():
                        tipo_param = param_ctx.tipo_base().getText().replace("^", "")
                    else:
                        tipo_param = param_ctx.tipo_identificado().getText().replace("^", "")
                    parametros.append((nome_param, tipo_param))
            
            # Registrar a função
            self.funcoes[nome_funcao] = {
                'tipo_retorno': tipo_retorno,
                'parametros': parametros
            }
        
        # Entrar no escopo da função
        self.escopo_atual = 'funcao'
        self.simbolos_locais = {}
        
        # Adicionar parâmetros ao escopo local
        if ctx.parametros():
            for param_ctx in ctx.parametros().parametro():
                nome_param = param_ctx.IDENT().getText()
                if param_ctx.tipo_base():
                    tipo_param = param_ctx.tipo_base().getText().replace("^", "")
                else:
                    tipo_param = param_ctx.tipo_identificado().getText().replace("^", "")
                self.simbolos_locais[nome_param] = tipo_param
                
                # Se o tipo é um registro definido pelo usuário, copiar seus campos
                if tipo_param in self.tipos_definidos and tipo_param in self.campos_registro:
                    self.campos_registro[nome_param] = self.campos_registro[tipo_param]

    def exitDeclaracao_funcao(self, ctx:LAParser.Declaracao_funcaoContext):
        # Sair do escopo da função
        self.escopo_atual = 'global'
        self.simbolos_locais = {}

    def enterDeclaracao_procedimento(self, ctx:LAParser.Declaracao_procedimentoContext):
        nome_procedimento = ctx.IDENT().getText()
        
        # Verificar se o procedimento já foi declarado
        if nome_procedimento in self.procedimentos or nome_procedimento in self.funcoes or nome_procedimento in self.simbolos:
            token_proc = ctx.IDENT().getSymbol()
            self.erros.append(f"Linha {self.linha_token(token_proc)}: identificador {nome_procedimento} ja declarado anteriormente")
        else:
            # Extrair parâmetros
            parametros = []
            if ctx.parametros():
                for param_ctx in ctx.parametros().parametro():
                    nome_param = param_ctx.IDENT().getText()
                    if param_ctx.tipo_base():
                        tipo_param = param_ctx.tipo_base().getText().replace("^", "")
                    else:
                        tipo_param = param_ctx.tipo_identificado().getText().replace("^", "")
                    parametros.append((nome_param, tipo_param))
            
            # Registrar o procedimento
            self.procedimentos[nome_procedimento] = {
                'parametros': parametros
            }
        
        # Entrar no escopo do procedimento
        self.escopo_atual = 'procedimento'
        self.simbolos_locais = {}
        
        # Adicionar parâmetros ao escopo local
        if ctx.parametros():
            for param_ctx in ctx.parametros().parametro():
                nome_param = param_ctx.IDENT().getText()
                if param_ctx.tipo_base():
                    tipo_param = param_ctx.tipo_base().getText().replace("^", "")
                else:
                    tipo_param = param_ctx.tipo_identificado().getText().replace("^", "")
                self.simbolos_locais[nome_param] = tipo_param
                
                # Se o tipo é um registro definido pelo usuário, copiar seus campos
                if tipo_param in self.tipos_definidos and tipo_param in self.campos_registro:
                    self.campos_registro[nome_param] = self.campos_registro[tipo_param]

    def exitDeclaracao_procedimento(self, ctx:LAParser.Declaracao_procedimentoContext):
        # Sair do escopo do procedimento
        self.escopo_atual = 'global'
        self.simbolos_locais = {}

    def enterRetorne(self, ctx:LAParser.RetorneContext):
        # Verificar se estamos em uma função (retorne só é permitido em funções)
        if self.escopo_atual != 'funcao':
            self.erros.append(f"Linha {ctx.start.line}: comando retorne nao permitido nesse escopo")
        
        # Processar a expressão de retorno
        self.tipo_expressao(ctx.expressao())

    def enterComandoenquanto(self, ctx: LAParser.ComandoenquantoContext):
        tipo_condicao = self.tipo_expressao(ctx.expressao())

    def enterComandose(self, ctx: LAParser.ComandoseContext):
        # Processar a expressão condicional
        tipo_condicao = self.tipo_expressao(ctx.expressao())

    # Verificar identificadores usados em 'leia' (leitura)
    def enterLeitura(self, ctx:LAParser.LeituraContext):
        lista_ids = ctx.lista_identificadores()
        for child in lista_ids.children:
            if child.getText() == ',':
                continue
            if isinstance(child, LAParser.Acesso_campoContext):
                # Validar acesso a campo
                self.validar_acesso_campo(child)
            elif hasattr(LAParser, 'Acesso_arrayContext') and isinstance(child, LAParser.Acesso_arrayContext):
                # Validar acesso a array
                self.validar_acesso_array(child)
            else:
                # É um identificador simples
                nome = child.getText()
                if nome not in self.simbolos:
                    token_id = child.getSymbol()
                    self.erros.append(f"Linha {self.linha_token(token_id)}: identificador {nome} nao declarado")

    def validar_acesso_campo(self, ctx):
        """Valida acesso a campo como variavel.campo"""
        if hasattr(ctx, 'IDENT') and ctx.IDENT():
            # Primeiro identificador é a variável
            nome_var = ctx.IDENT(0).getText()
            nome_campo = ctx.IDENT(1).getText()
            
            # Verificar se a variável existe (primeiro local, depois global)
            if nome_var not in self.simbolos_locais and nome_var not in self.simbolos:
                token_var = ctx.IDENT(0).getSymbol()
                self.erros.append(f"Linha {self.linha_token(token_var)}: identificador {nome_var}.{nome_campo} nao declarado")
                return
            
            # Verificar se a variável tem campos (é um registro)
            if nome_var in self.campos_registro:
                campos = self.campos_registro[nome_var]
                if nome_campo not in campos:
                    token_campo = ctx.IDENT(1).getSymbol()
                    self.erros.append(f"Linha {self.linha_token(token_campo)}: identificador {nome_var}.{nome_campo} nao declarado")
            else:
                # Variável não é um registro
                token_campo = ctx.IDENT(1).getSymbol()
                self.erros.append(f"Linha {self.linha_token(token_campo)}: identificador {nome_var}.{nome_campo} nao declarado")

    def validar_acesso_array(self, ctx):
        """Valida acesso a array como variavel[indice]"""
        if hasattr(ctx, 'IDENT') and ctx.IDENT():
            nome_var = ctx.IDENT().getText()
            
            # Verificar se a variável existe
            if nome_var not in self.simbolos:
                token_var = ctx.IDENT().getSymbol()
                self.erros.append(f"Linha {self.linha_token(token_var)}: identificador {nome_var} nao declarado")
                return
            
            # Verificar se o índice é um inteiro
            tipo_indice = self.tipo_expressao(ctx.expressao())
            if tipo_indice and tipo_indice != 'inteiro':
                # Não reportar erro aqui se o tipo não for conhecido, apenas se for conhecido e diferente de inteiro
                pass

    def enterChamada_procedimento(self, ctx:LAParser.Chamada_procedimentoContext):
        """Valida chamadas de procedimento"""
        nome_procedimento = ctx.IDENT().getText()
        
        # Verificar se o procedimento existe
        if nome_procedimento not in self.procedimentos:
            self.erros.append(f"Linha {ctx.start.line}: identificador {nome_procedimento} nao declarado")
            return
        
        # Obter informações do procedimento
        info_procedimento = self.procedimentos[nome_procedimento]
        parametros_esperados = info_procedimento['parametros']
        
        # Verificar parâmetros passados
        parametros_passados = []
        if ctx.lista_expressao():
            for exp in ctx.lista_expressao().expressao():
                tipo_param = self.tipo_expressao(exp)
                parametros_passados.append(tipo_param)
        
        # Validar número de parâmetros
        if len(parametros_passados) != len(parametros_esperados):
            self.erros.append(f"Linha {ctx.start.line}: incompatibilidade de parametros na chamada de {nome_procedimento}")
            return
        
        # Validar tipos dos parâmetros
        for i, (tipo_passado, (_, tipo_esperado)) in enumerate(zip(parametros_passados, parametros_esperados)):
            if tipo_passado and tipo_passado != tipo_esperado:  # Exigir compatibilidade exata para parâmetros
                self.erros.append(f"Linha {ctx.start.line}: incompatibilidade de parametros na chamada de {nome_procedimento}")
                break


    # Verificar identificadores usados em 'escreva'
    # Pode ser extendido para expressões, mas simplificado aqui (por token de IDENT)
    def enterEscrita(self, ctx:LAParser.EscritaContext):
        for exp in ctx.expressao():
            self.tipo_expressao(exp)

def main():
    if len(sys.argv) != 3:
        print("Uso: python3 analisador_semantico.py entrada.txt saida.txt")
        return

    arquivo_entrada = sys.argv[1]
    arquivo_saida = sys.argv[2]

    input_stream = FileStream(arquivo_entrada, encoding='utf-8')
    lexer = LALexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = LAParser(token_stream)

    tree = parser.programa()

    analisador = AnalisadorSemantico(token_stream)
    walker = ParseTreeWalker()
    walker.walk(analisador, tree)

    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        for erro in analisador.erros:
            f.write(erro + '\n')
        f.write("Fim da compilacao\n")

if __name__ == "__main__":
    main()
