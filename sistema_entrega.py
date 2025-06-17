"""
Sistema de Entrega Automática
Módulo para envio por e-mail e geração de links de download
"""

import smtplib
import os
import uuid
import hashlib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import sqlite3
import json

class SistemaEntrega:
    def __init__(self, downloads_path='downloads'):
        self.downloads_path = downloads_path
        os.makedirs(downloads_path, exist_ok=True)
        
        # Configurações de e-mail (substitua pelos dados reais)
        self.smtp_server = "smtp.gmail.com"  # ou outro servidor SMTP
        self.smtp_port = 587
        self.email_usuario = "despede.ai@hotmail.com"
        self.email_senha = "sua_senha_app"  # Use senha de app
        
        self.init_database()
    
    def init_database(self):
        """Inicializa banco para controle de downloads"""
        conn = sqlite3.connect('downloads.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id TEXT PRIMARY KEY,
                transacao_id TEXT,
                email TEXT,
                arquivo_path TEXT,
                download_token TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                download_count INTEGER DEFAULT 0,
                max_downloads INTEGER DEFAULT 3
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def gerar_token_download(self):
        """Gera token único para download"""
        return str(uuid.uuid4()).replace('-', '')
    
    def salvar_arquivo_download(self, arquivo_buffer, nome_arquivo, transacao_id):
        """Salva arquivo para download e gera token"""
        
        # Gera nome único para o arquivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_unico = f"{timestamp}_{nome_arquivo}"
        arquivo_path = os.path.join(self.downloads_path, nome_unico)
        
        # Salva arquivo
        with open(arquivo_path, 'wb') as f:
            f.write(arquivo_buffer.getvalue())
        
        # Gera token de download
        download_token = self.gerar_token_download()
        
        # Salva no banco
        conn = sqlite3.connect('downloads.db')
        cursor = conn.cursor()
        
        download_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(days=7)  # Expira em 7 dias
        
        cursor.execute('''
            INSERT INTO downloads 
            (id, transacao_id, arquivo_path, download_token, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (download_id, transacao_id, arquivo_path, download_token, expires_at))
        
        conn.commit()
        conn.close()
        
        return {
            'download_id': download_id,
            'download_token': download_token,
            'expires_at': expires_at.isoformat()
        }
    
    def gerar_link_download(self, download_token, base_url="https://despedeai.site"):
        """Gera link de download"""
        return f"{base_url}/download/{download_token}"
    
    def processar_download(self, download_token):
        """Processa solicitação de download"""
        conn = sqlite3.connect('downloads.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, arquivo_path, expires_at, download_count, max_downloads
            FROM downloads 
            WHERE download_token = ?
        ''', (download_token,))
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return {'error': 'Token inválido'}
        
        download_id, arquivo_path, expires_at, download_count, max_downloads = result
        
        # Verifica se expirou
        if datetime.now() > datetime.fromisoformat(expires_at):
            conn.close()
            return {'error': 'Link expirado'}
        
        # Verifica limite de downloads
        if download_count >= max_downloads:
            conn.close()
            return {'error': 'Limite de downloads excedido'}
        
        # Verifica se arquivo existe
        if not os.path.exists(arquivo_path):
            conn.close()
            return {'error': 'Arquivo não encontrado'}
        
        # Incrementa contador
        cursor.execute('''
            UPDATE downloads 
            SET download_count = download_count + 1
            WHERE id = ?
        ''', (download_id,))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'arquivo_path': arquivo_path,
            'downloads_restantes': max_downloads - download_count - 1
        }
    
    def enviar_email_kit(self, email_destino, dados_usuario, link_download):
        """Envia e-mail com o kit de rescisão"""
        
        try:
            # Cria mensagem
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_usuario
            msg['To'] = email_destino
            msg['Subject'] = "🎉 Seu Kit Rescisão Premium está pronto!"
            
            # Corpo do e-mail em HTML
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                             color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 30px; }}
                    .download-box {{ background: white; padding: 20px; border-radius: 10px; 
                                   text-align: center; margin: 20px 0; border: 2px solid #28a745; }}
                    .download-btn {{ display: inline-block; background: #28a745; color: white; 
                                   padding: 15px 30px; text-decoration: none; border-radius: 5px; 
                                   font-weight: bold; margin: 10px 0; }}
                    .footer {{ background: #343a40; color: white; padding: 20px; text-align: center; 
                             border-radius: 0 0 10px 10px; }}
                    .kit-items {{ background: white; padding: 20px; border-radius: 10px; margin: 20px 0; }}
                    .item {{ margin: 10px 0; padding: 10px; border-left: 4px solid #007bff; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎉 DESPEDE AI</h1>
                        <h2>Seu Kit Rescisão Premium</h2>
                        <p>Olá, {dados_usuario.get('nome', 'Cliente')}!</p>
                    </div>
                    
                    <div class="content">
                        <p>Parabéns! Seu <strong>Kit Rescisão Premium</strong> foi gerado com sucesso e está pronto para download.</p>
                        
                        <div class="download-box">
                            <h3>📦 Faça o Download Agora</h3>
                            <p>Clique no botão abaixo para baixar seu kit completo:</p>
                            <a href="{link_download}" class="download-btn">BAIXAR MEU KIT</a>
                            <p><small>⏰ Link válido por 7 dias | Máximo 3 downloads</small></p>
                        </div>
                        
                        <div class="kit-items">
                            <h3>📋 O que está incluído no seu kit:</h3>
                            
                            <div class="item">
                                <strong>📄 Relatório Personalizado (PDF)</strong><br>
                                Análise detalhada da sua rescisão com cálculos precisos e estratégias personalizadas.
                            </div>
                            
                            <div class="item">
                                <strong>📝 Modelos Prontos (DOCX)</strong><br>
                                • Recibo de quitação de verbas<br>
                                • Requerimento de saque do FGTS<br>
                                • Carta de negociação com empregador
                            </div>
                            
                            <div class="item">
                                <strong>📊 Planilha Financeira (XLSX)</strong><br>
                                Controle de verbas, planejamento financeiro e simulador de investimentos.
                            </div>
                            
                            <div class="item">
                                <strong>💡 Guia Estratégico (PDF)</strong><br>
                                "Como negociar sua demissão" com checklist pós-demissão.
                            </div>
                        </div>
                        
                        <div style="background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107;">
                            <strong>⚠️ Importante:</strong> Guarde bem este e-mail! O link de download é único e pessoal.
                            Em caso de problemas, entre em contato conosco.
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p><strong>DESPEDE AI</strong> - Sua rescisão trabalhista simplificada</p>
                        <p>📧 Suporte: despede.ai@hotmail.com</p>
                        <p>🌐 www.despedeai.site</p>
                        <p><small>© 2025 - Todos os direitos reservados</small></p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Versão texto simples
            text_body = f"""
            DESPEDE AI - Kit Rescisão Premium
            
            Olá, {dados_usuario.get('nome', 'Cliente')}!
            
            Seu Kit Rescisão Premium foi gerado com sucesso!
            
            DOWNLOAD: {link_download}
            
            O kit inclui:
            - Relatório Personalizado (PDF)
            - Modelos Prontos (DOCX)
            - Planilha Financeira (XLSX)
            - Guia Estratégico (PDF)
            
            Link válido por 7 dias | Máximo 3 downloads
            
            Suporte: despede.ai@hotmail.com
            www.despedeai.site
            """
            
            # Anexa ambas as versões
            msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            
            # Envia e-mail
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_usuario, self.email_senha)
            
            text = msg.as_string()
            server.sendmail(self.email_usuario, email_destino, text)
            server.quit()
            
            return {'success': True, 'message': 'E-mail enviado com sucesso'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def processar_entrega_completa(self, transacao_id, arquivo_kit, dados_usuario, email_destino):
        """Processa entrega completa: salva arquivo, gera link e envia e-mail"""
        
        try:
            # 1. Salva arquivo para download
            nome_arquivo = f"Kit_Rescisao_Premium_{dados_usuario.get('nome', 'Usuario').replace(' ', '_')}.zip"
            download_info = self.salvar_arquivo_download(arquivo_kit, nome_arquivo, transacao_id)
            
            # 2. Gera link de download
            link_download = self.gerar_link_download(download_info['download_token'])
            
            # 3. Envia e-mail
            email_result = self.enviar_email_kit(email_destino, dados_usuario, link_download)
            
            if email_result['success']:
                return {
                    'success': True,
                    'download_link': link_download,
                    'download_token': download_info['download_token'],
                    'expires_at': download_info['expires_at']
                }
            else:
                return {
                    'success': False,
                    'error': f"Erro ao enviar e-mail: {email_result['error']}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Erro na entrega: {str(e)}"
            }
    
    def reenviar_kit(self, download_token, email_destino):
        """Reenvia kit para o e-mail (máximo 2 reenvios)"""
        
        conn = sqlite3.connect('downloads.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT transacao_id, expires_at FROM downloads 
            WHERE download_token = ?
        ''', (download_token,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return {'success': False, 'error': 'Token inválido'}
        
        transacao_id, expires_at = result
        
        # Verifica se expirou
        if datetime.now() > datetime.fromisoformat(expires_at):
            return {'success': False, 'error': 'Link expirado'}
        
        # Gera link e reenvia
        link_download = self.gerar_link_download(download_token)
        
        # Dados básicos para o e-mail
        dados_usuario = {'nome': 'Cliente'}  # Poderia buscar do banco se necessário
        
        return self.enviar_email_kit(email_destino, dados_usuario, link_download)
    
    def limpar_arquivos_expirados(self):
        """Remove arquivos expirados do sistema"""
        conn = sqlite3.connect('downloads.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT arquivo_path FROM downloads 
            WHERE expires_at < CURRENT_TIMESTAMP
        ''')
        
        arquivos_expirados = cursor.fetchall()
        
        # Remove arquivos físicos
        removidos = 0
        for (arquivo_path,) in arquivos_expirados:
            try:
                if os.path.exists(arquivo_path):
                    os.remove(arquivo_path)
                    removidos += 1
            except Exception as e:
                print(f"Erro ao remover {arquivo_path}: {e}")
        
        # Remove registros do banco
        cursor.execute('''
            DELETE FROM downloads 
            WHERE expires_at < CURRENT_TIMESTAMP
        ''')
        
        conn.commit()
        conn.close()
        
        return removidos

