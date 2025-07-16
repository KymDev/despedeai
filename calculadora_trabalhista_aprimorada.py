from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import calendar

class CalculadoraTrabalhistaAprimorada:
    def __init__(self):
        # Alíquotas INSS 2025 (atualizadas)
        self.inss_faixas = [
            (Decimal('1412.00'), Decimal('0.075')),  # 7.5%
            (Decimal('2666.68'), Decimal('0.09')),   # 9%
            (Decimal('4000.03'), Decimal('0.12')),   # 12%
            (Decimal('7786.02'), Decimal('0.14'))    # 14%
        ]
        
        # Alíquotas IRRF 2025 (atualizadas)
        self.irrf_faixas = [
            (Decimal('2259.20'), Decimal('0.00'), Decimal('0.00')),      # Isento
            (Decimal('2826.65'), Decimal('0.075'), Decimal('169.44')),   # 7.5%
            (Decimal('3751.05'), Decimal('0.15'), Decimal('381.44')),    # 15%
            (Decimal('4664.68'), Decimal('0.225'), Decimal('662.77')),   # 22.5%
            (float('inf'), Decimal('0.275'), Decimal('896.00'))          # 27.5%
        ]
        
        # Valores atualizados para 2025
        self.salario_minimo = Decimal('1412.00')
        self.valor_dependente_ir = Decimal('189.59')
        self.teto_inss = Decimal('7786.02')
        
        # Percentuais de horas extras
        self.percentuais_he = {
            'normal': Decimal('0.50'),      # 50% - dias úteis
            'noturna': Decimal('0.20'),     # 20% adicional noturno
            'domingo': Decimal('1.00'),     # 100% - domingos e feriados
            'dsr': Decimal('1.00')          # DSR sobre horas extras
        }
        
        # Percentuais de adicionais
        self.percentuais_adicionais = {
            'periculosidade': Decimal('0.30'),  # 30%
            'insalubridade_minimo': Decimal('0.10'),    # 10% grau mínimo
            'insalubridade_medio': Decimal('0.20'),     # 20% grau médio
            'insalubridade_maximo': Decimal('0.40'),    # 40% grau máximo
            'noturno': Decimal('0.20')       # 20%
        }
    
    def calcular_inss(self, salario_base):
        """Calcula o desconto do INSS com base nas faixas progressivas"""
        salario = Decimal(str(salario_base))
        desconto_total = Decimal('0')
        salario_restante = salario
        
        for i, (teto, aliquota) in enumerate(self.inss_faixas):
            if salario_restante <= 0:
                break
                
            if i == 0:
                base_calculo = min(salario_restante, teto)
            else:
                faixa_anterior = self.inss_faixas[i-1][0]
                base_calculo = min(salario_restante, teto - faixa_anterior)
            
            desconto_faixa = base_calculo * aliquota
            desconto_total += desconto_faixa
            salario_restante -= base_calculo
            
        return desconto_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def calcular_irrf(self, base_calculo, dependentes=0):
        """Calcula o desconto do IRRF"""
        base = Decimal(str(base_calculo))
        deducao_dependentes = self.valor_dependente_ir * dependentes
        base_tributavel = base - deducao_dependentes
        
        if base_tributavel <= 0:
            return Decimal('0')
        
        for teto, aliquota, deducao in self.irrf_faixas:
            if base_tributavel <= teto:
                imposto = (base_tributavel * aliquota) - deducao
                return max(Decimal('0'), imposto).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return Decimal('0')
    
    def calcular_horas_extras(self, salario_base, horas_extras_mes, tipo_he='normal'):
        """
        Calcula horas extras com diferentes tipos
        tipo_he: 'normal', 'noturna', 'domingo'
        """
        salario = Decimal(str(salario_base))
        horas = Decimal(str(horas_extras_mes))
        
        # Valor da hora normal (220 horas mensais)
        valor_hora = salario / 220
        
        # Percentual conforme o tipo
        percentual = self.percentuais_he.get(tipo_he, self.percentuais_he['normal'])
        
        # Valor da hora extra
        valor_hora_extra = valor_hora * (1 + percentual)
        
        # Total de horas extras
        total_he = valor_hora_extra * horas
        
        return {
            'valor_hora_normal': valor_hora.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'valor_hora_extra': valor_hora_extra.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'total_horas_extras': total_he.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'horas': horas,
            'tipo': tipo_he
        }
    
    def calcular_dsr_horas_extras(self, valor_he_mes, dias_uteis_mes=22):
        """Calcula DSR sobre horas extras"""
        valor_he = Decimal(str(valor_he_mes))
        dias_uteis = Decimal(str(dias_uteis_mes))
        
        # DSR = (Valor HE / Dias úteis) * Domingos e feriados (aprox. 8 por mês)
        dsr = (valor_he / dias_uteis) * 8
        
        return {
            'valor_dsr': dsr.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'base_calculo': valor_he,
            'dias_uteis': dias_uteis
        }
    
    def calcular_adicional(self, salario_base, tipo_adicional, base_calculo='salario'):
        """
        Calcula adicionais (periculosidade, insalubridade, noturno)
        base_calculo: 'salario' ou 'salario_minimo'
        """
        if base_calculo == 'salario_minimo':
            base = self.salario_minimo
        else:
            base = Decimal(str(salario_base))
        
        percentual = self.percentuais_adicionais.get(tipo_adicional, Decimal('0'))
        valor_adicional = base * percentual
        
        return {
            'tipo': tipo_adicional,
            'base_calculo': base,
            'percentual': percentual * 100,  # Para exibição em %
            'valor': valor_adicional.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        }
    
    def calcular_ferias_proporcionais(self, salario, data_admissao, data_demissao, ferias_vencidas=0):
        """Calcula férias proporcionais + 1/3 constitucional (aprimorado)"""
        salario = Decimal(str(salario))
        
        # Calcula períodos aquisitivos completos
        anos_completos = 0
        data_atual = data_admissao
        
        while data_atual + timedelta(days=365) <= data_demissao:
            anos_completos += 1
            data_atual += timedelta(days=365)
        
        # Período aquisitivo atual (incompleto)
        data_inicio_periodo = data_atual
        
        # Calcula meses trabalhados no período atual
        meses_trabalhados = 0
        data_mes = data_inicio_periodo
        
        while data_mes < data_demissao:
            if data_mes.month == 12:
                proximo_mes = data_mes.replace(year=data_mes.year + 1, month=1, day=1)
            else:
                proximo_mes = data_mes.replace(month=data_mes.month + 1, day=1)
            
            if proximo_mes <= data_demissao:
                meses_trabalhados += 1
            elif (data_demissao - data_mes).days >= 15:
                meses_trabalhados += 1
                
            data_mes = proximo_mes
        
        # Calcula valor proporcional
        valor_ferias = (salario * meses_trabalhados) / 12
        um_terco = valor_ferias / 3
        
        # Férias vencidas (se houver)
        valor_ferias_vencidas = Decimal(str(ferias_vencidas)) * salario
        um_terco_vencidas = valor_ferias_vencidas / 3
        
        return {
            'anos_completos': anos_completos,
            'meses_trabalhados': meses_trabalhados,
            'valor_ferias_proporcionais': valor_ferias.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'um_terco_proporcionais': um_terco.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'valor_ferias_vencidas': valor_ferias_vencidas.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'um_terco_vencidas': um_terco_vencidas.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'total': (valor_ferias + um_terco + valor_ferias_vencidas + um_terco_vencidas).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        }
    
    def calcular_decimo_terceiro(self, salario, data_admissao, data_demissao, decimo_vencido=False):
        """Calcula 13º salário proporcional (aprimorado)"""
        salario = Decimal(str(salario))
        
        # 13º do ano anterior (se vencido)
        valor_vencido = salario if decimo_vencido else Decimal('0')
        
        # 13º proporcional do ano atual
        meses_trabalhados = data_demissao.month
        
        # Se trabalhou mais de 15 dias no mês da demissão, conta o mês
        if data_demissao.day >= 15:
            meses_trabalhados = data_demissao.month
        else:
            meses_trabalhados = data_demissao.month - 1
        
        # Se foi admitido no ano atual, ajusta o cálculo
        if data_admissao.year == data_demissao.year:
            meses_desde_admissao = data_demissao.month - data_admissao.month
            if data_admissao.day <= 15:
                meses_desde_admissao += 1
            meses_trabalhados = min(meses_trabalhados, meses_desde_admissao)
        
        valor_proporcional = (salario * meses_trabalhados) / 12
        
        return {
            'meses_trabalhados': meses_trabalhados,
            'valor_proporcional': valor_proporcional.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'valor_vencido': valor_vencido.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'total': (valor_proporcional + valor_vencido).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        }
    
    def calcular_aviso_previo(self, salario, tempo_servico_anos, tipo_demissao, trabalhado=False):
        """Calcula aviso prévio (30 dias + 3 dias por ano) - aprimorado"""
        salario = Decimal(str(salario))
        
        if tipo_demissao in ['justa_causa', 'pedido_demissao']:
            return {
                'dias': 0,
                'valor': Decimal('0'),
                'tipo': 'Não aplicável',
                'motivo': 'Não há direito ao aviso prévio neste tipo de rescisão'
            }
        
        # 30 dias base + 3 dias por ano trabalhado
        dias_aviso = 30 + (tempo_servico_anos * 3)
        dias_aviso = min(dias_aviso, 90)  # Máximo 90 dias
        
        valor_aviso = (salario * dias_aviso) / 30
        
        tipo_aviso = 'Trabalhado' if trabalhado else 'Indenizado'
        
        # Se for rescisão por acordo, aviso prévio é reduzido pela metade
        if tipo_demissao == 'acordo':
            valor_aviso = valor_aviso / 2
            tipo_aviso += ' (50% - Acordo)'
        
        return {
            'dias': dias_aviso,
            'valor': valor_aviso.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'tipo': tipo_aviso,
            'tempo_servico_anos': tempo_servico_anos
        }
    
    def calcular_multa_fgts(self, saldo_fgts, tipo_demissao):
        """Calcula multa de 40% do FGTS (aprimorado)"""
        saldo = Decimal(str(saldo_fgts))
        
        if tipo_demissao == 'sem_justa_causa':
            percentual = 40
            multa = saldo * Decimal('0.40')
        elif tipo_demissao == 'acordo':
            percentual = 20  # Rescisão por acordo
            multa = saldo * Decimal('0.20')
        else:
            percentual = 0
            multa = Decimal('0')
        
        return {
            'percentual': percentual,
            'valor': multa.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'aplicavel': percentual > 0,
            'saldo_base': saldo,
            'tipo_demissao': tipo_demissao
        }
    
    def calcular_saldo_salario(self, salario, data_demissao, dias_trabalhados_mes=None):
        """Calcula saldo de salário do mês (aprimorado)"""
        salario = Decimal(str(salario))
        
        if dias_trabalhados_mes is None:
            dias_trabalhados_mes = data_demissao.day
        
        dias_mes = calendar.monthrange(data_demissao.year, data_demissao.month)[1]
        
        valor_saldo = (salario * dias_trabalhados_mes) / dias_mes
        
        return {
            'dias_trabalhados': dias_trabalhados_mes,
            'dias_mes': dias_mes,
            'valor_dia': (salario / dias_mes).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'valor': valor_saldo.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        }
    
    def calcular_rescisao_completa(self, dados):
        """
        Calcula todas as verbas rescisórias (versão aprimorada)
        
        dados = {
            'salario': float,
            'data_admissao': datetime,
            'data_demissao': datetime,
            'tipo_demissao': 'sem_justa_causa' | 'justa_causa' | 'pedido_demissao' | 'acordo',
            'saldo_fgts': float,
            'horas_extras_mes': float (opcional),
            'tipo_horas_extras': str (opcional),
            'adicional_noturno': float (opcional),
            'adicional_periculosidade': float (opcional),
            'adicional_insalubridade': float (opcional),
            'tipo_insalubridade': str (opcional),
            'dependentes_ir': int (opcional),
            'aviso_trabalhado': bool (opcional),
            'ferias_vencidas': int (opcional),
            'decimo_vencido': bool (opcional),
            'dias_trabalhados_mes': int (opcional)
        }
        """
        
        # Dados básicos
        salario = Decimal(str(dados['salario']))
        data_admissao = dados['data_admissao']
        data_demissao = dados['data_demissao']
        tipo_demissao = dados['tipo_demissao']
        
        # Calcula tempo de serviço
        tempo_servico = data_demissao - data_admissao
        tempo_servico_anos = tempo_servico.days // 365
        
        # Cálculos individuais
        saldo_salario = self.calcular_saldo_salario(
            salario, 
            data_demissao, 
            dados.get('dias_trabalhados_mes')
        )
        
        ferias = self.calcular_ferias_proporcionais(
            salario, 
            data_admissao, 
            data_demissao,
            dados.get('ferias_vencidas', 0)
        )
        
        decimo_terceiro = self.calcular_decimo_terceiro(
            salario, 
            data_admissao, 
            data_demissao,
            dados.get('decimo_vencido', False)
        )
        
        aviso_previo = self.calcular_aviso_previo(
            salario, 
            tempo_servico_anos, 
            tipo_demissao, 
            dados.get('aviso_trabalhado', False)
        )
        
        multa_fgts = self.calcular_multa_fgts(
            dados.get('saldo_fgts', 0), 
            tipo_demissao
        )
        
        # Horas extras (se houver)
        horas_extras = {'total_horas_extras': Decimal('0'), 'dsr': {'valor_dsr': Decimal('0')}}
        if dados.get('horas_extras_mes', 0) > 0:
            tipo_he = dados.get('tipo_horas_extras', 'normal')
            horas_extras = self.calcular_horas_extras(
                salario, 
                dados['horas_extras_mes'], 
                tipo_he
            )
            # Calcula DSR sobre horas extras
            horas_extras['dsr'] = self.calcular_dsr_horas_extras(
                horas_extras['total_horas_extras']
            )
        
        # Adicionais
        adicional_noturno = {'valor': Decimal('0')}
        if dados.get('adicional_noturno', 0) > 0:
            adicional_noturno = self.calcular_adicional(
                salario, 
                'noturno'
            )
        
        adicional_periculosidade = {'valor': Decimal('0')}
        if dados.get('adicional_periculosidade', 0) > 0:
            adicional_periculosidade = self.calcular_adicional(
                salario, 
                'periculosidade'
            )
        
        adicional_insalubridade = {'valor': Decimal('0')}
        if dados.get('adicional_insalubridade', 0) > 0:
            tipo_insalubridade = dados.get('tipo_insalubridade', 'insalubridade_minimo')
            adicional_insalubridade = self.calcular_adicional(
                salario, 
                tipo_insalubridade,
                'salario_minimo'  # Insalubridade é calculada sobre o salário mínimo
            )
        
        # Total bruto
        total_bruto = (
            saldo_salario['valor'] +
            ferias['total'] +
            decimo_terceiro['total'] +
            aviso_previo['valor'] +
            horas_extras['total_horas_extras'] +
            horas_extras['dsr']['valor_dsr'] +
            adicional_noturno['valor'] +
            adicional_periculosidade['valor'] +
            adicional_insalubridade['valor']
        )
        
        # Descontos
        base_inss = total_bruto
        desconto_inss = self.calcular_inss(base_inss)
        
        base_irrf = total_bruto - desconto_inss
        desconto_irrf = self.calcular_irrf(base_irrf, dados.get('dependentes_ir', 0))
        
        total_descontos = desconto_inss + desconto_irrf
        total_liquido = total_bruto - total_descontos
        
        return {
            'verbas': {
                'saldo_salario': saldo_salario,
                'ferias_proporcionais': ferias,
                'decimo_terceiro': decimo_terceiro,
                'aviso_previo': aviso_previo,
                'horas_extras': horas_extras,
                'adicional_noturno': adicional_noturno,
                'adicional_periculosidade': adicional_periculosidade,
                'adicional_insalubridade': adicional_insalubridade,
                'multa_fgts': multa_fgts
            },
            'resumo': {
                'total_bruto': total_bruto.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'desconto_inss': desconto_inss,
                'desconto_irrf': desconto_irrf,
                'total_descontos': total_descontos.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'total_liquido': total_liquido.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            },
            'tempo_servico': {
                'anos': tempo_servico_anos,
                'meses': (tempo_servico.days % 365) // 30,
                'dias_totais': tempo_servico.days
            },
            'informacoes_legais': {
                'salario_minimo': self.salario_minimo,
                'teto_inss': self.teto_inss,
                'valor_dependente_ir': self.valor_dependente_ir
            }
        }
    
    def gerar_relatorio_detalhado(self, resultado_calculo, dados_usuario):
        """Gera um relatório detalhado em formato de dicionário para exibição"""
        
        relatorio = {
            'cabecalho': {
                'titulo': 'Relatório de Cálculo de Rescisão Trabalhista',
                'data_geracao': datetime.now().strftime('%d/%m/%Y às %H:%M'),
                'funcionario': dados_usuario.get('nome', 'N/A'),
                'empresa': dados_usuario.get('empresa', 'N/A')
            },
            'dados_contratuais': {
                'cargo': dados_usuario.get('cargo', 'N/A'),
                'salario': dados_usuario.get('salario', 0),
                'data_admissao': dados_usuario.get('data_admissao', 'N/A'),
                'data_demissao': dados_usuario.get('data_demissao', 'N/A'),
                'tempo_servico': resultado_calculo['tempo_servico'],
                'tipo_demissao': dados_usuario.get('tipo_demissao', 'N/A')
            },
            'verbas_detalhadas': resultado_calculo['verbas'],
            'resumo_financeiro': resultado_calculo['resumo'],
            'observacoes': [
                'Este cálculo é uma estimativa baseada na legislação vigente.',
                'Consulte sempre um contador ou advogado trabalhista para validação.',
                'Valores podem variar conforme acordos coletivos específicos.',
                'Prazos para pagamento: até 1º dia útil após a rescisão (aviso trabalhado) ou até 10º dia (aviso indenizado).'
            ]
        }
        
        return relatorio
