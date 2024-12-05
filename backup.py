import os
import shutil
import tkinter as tk
from tkinter import PhotoImage
from tkinter import filedialog, messagebox
import schedule
import time
from datetime import datetime, timedelta
import threading
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw
import sqlite3


janela = None
#  SQLite
conn = sqlite3.connect('backup_config.db')
c = conn.cursor()
# Criar tabela
c.execute('''CREATE TABLE IF NOT EXISTS configuracoes
             (origem TEXT, destino TEXT, horario TEXT, dias_semana TEXT)''')
conn.commit()

dias_da_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

def salvar_configuracoes():
    dias_semana = ','.join([dia for dia, var in zip(dias_da_semana, semana_vars) if var.get()])
    c.execute('DELETE FROM configuracoes')
    c.execute('INSERT INTO configuracoes (origem, destino, horario, dias_semana) VALUES (?, ?, ?, ?)',
              (origem_var.get(), destino_var.get(), horario_var.get(), dias_semana))
    conn.commit()

def carregar_configuracoes():
    c.execute('SELECT * FROM configuracoes')
    row = c.fetchone()
    if row:
        origem_var.set(row[0])
        destino_var.set(row[1])
        horario_var.set(row[2])
        dias_semana = row[3].split(',')
        for dia, var in zip(dias_da_semana, semana_vars):
            var.set(dia in dias_semana)


def copiar_arquivos(origem, destino, chamada_inicial=True):
    try:
        data_atual = datetime.now()
        # Data de 15 dias atrás
        data_limite = data_atual - timedelta(days=15)

        for item in os.listdir(origem):
            origem_item = os.path.join(origem, item)
            destino_item = os.path.join(destino, item)

            if os.path.isdir(origem_item):
                if not os.path.exists(destino_item):
                    os.makedirs(destino_item)
                # Chamada recursiva para subdiretórios
                copiar_arquivos(origem_item, destino_item, chamada_inicial=False)
            else:
                # Verificar a data de modificação do arquivo
                data_modificacao = datetime.fromtimestamp(os.path.getmtime(origem_item))

                # Copiar apenas se o arquivo foi modificado nos últimos 15 dias
                if data_modificacao >= data_limite:
                    # Obter o nome e a extensão do arquivo
                    nome_arquivo, extensao = os.path.splitext(item)

                    # Formatar a data de modificação para o formato desejado
                    data_formatada = data_modificacao.strftime('%d%m%Y')

                    # Criar o novo nome do arquivo com a data de modificação
                    novo_nome = f"{nome_arquivo}_popBkp_{data_formatada}{extensao}"

                    # Caminho do arquivo de destino com o novo nome
                    destino_item = os.path.join(destino, novo_nome)

                    # Copiar o arquivo com o novo nome
                    shutil.copy2(origem_item, destino_item)

        # Exibir mensagem de sucesso apenas na primeira chamada
        if chamada_inicial:
            messagebox.showinfo("CloudPOP - Backup", "Backup concluído com sucesso!")
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro durante o backup: {e}")



# janela de origem
def selecionar_origem():
    origem = filedialog.askdirectory(title="Selecionar a pasta de origem")
    if origem:
        origem_var.set(origem)

# janela de destino
def selecionar_destino():
    destino = filedialog.askdirectory(title="Selecionar a pasta de destino")
    if destino:
        destino_var.set(destino)

def agendar_backup():
    horario = horario_var.get()
    if not horario:
        messagebox.showwarning("Aviso", "Por favor, insira um horário válido!")
        return
    dias_da_semana = [var.get() for var in semana_vars]
    if not any(dias_da_semana):
        messagebox.showwarning("Aviso", "Selecione pelo menos um dia da semana!")
        return
    # Mapear os dias da semana para os métodos do `schedule`
    dias_map = {
        "mon": schedule.every().monday,
        "tue": schedule.every().tuesday,
        "wed": schedule.every().wednesday,
        "thu": schedule.every().thursday,
        "fri": schedule.every().friday,
        "sat": schedule.every().saturday,
        "sun": schedule.every().sunday,
    }
    # Agendar o backup para os dias selecionados
    for dia, selecionado in zip(dias_map.keys(), dias_da_semana):
        if selecionado:
            dias_map[dia].at(horario).do(backup_imediato)
    messagebox.showinfo("Agendamento", "Backup agendado com sucesso!")


def backup_imediato():
    origem = origem_var.get()
    destino = destino_var.get()
    if origem and destino:
        copiar_arquivos(origem, destino)


# Função para manter o agendamento rodando em uma thread
def rodar_agendamentos():
    while True:
        schedule.run_pending()
        time.sleep(1)

def aplicar_mascara_horario(event):
    texto = horario_var.get()
    novo_texto = ""
    # Obter a posição atual do cursor
    posicao_cursor = event.widget.index(tk.INSERT)
    # Remover caracteres não numéricos
    for char in texto:
        if char.isdigit():
            novo_texto += char
    # Adicionar os dois pontos na posição correta
    if len(novo_texto) >= 4:
        novo_texto = novo_texto[:2] + ":" + novo_texto[2:5]
    if len(novo_texto) >= 5:
        novo_texto = novo_texto[:5]
    # Atualizar o texto do Entry
    horario_var.set(novo_texto)
    # Ajustar a posição do cursor
    nova_posicao_cursor = posicao_cursor
    # Se o cursor estava antes ou na posição dos dois pontos, mantenha-o; caso contrário, ajuste.
    if posicao_cursor == 4:
        nova_posicao_cursor += 1
    elif posicao_cursor > len(novo_texto):
        nova_posicao_cursor = len(novo_texto)
    # Redefinir a posição do cursor
    event.widget.icursor(nova_posicao_cursor)

    # Valida o horário ao finalizar a digitação (quando o texto tem 5 caracteres)
    if len(novo_texto) == 5:
        validar_horario(novo_texto)

def validar_horario(horario):
    """Valida o horário no formato HH:MM e exibe mensagem de erro se inválido."""
    try:
        partes = horario.split(":")
        if len(partes) != 2:
            raise ValueError("Formato inválido.")        
        horas, minutos = int(partes[0]), int(partes[1])        
        # Verifica se as horas e os minutos estão dentro dos limites
        if not (0 <= horas <= 23 and 0 <= minutos <= 59):
            raise ValueError("Horário fora dos limites permitidos.")
    except ValueError as e:
        messagebox.showerror("Erro de Horário", f"Horário inválido: {e}")
        horario_var.set("") 



def abrir_janela(icon):
    if janela == None:
        criar_janela()
    else:
        if janela.state() == 'withdrawn':            
            janela.deiconify()
            janela.lift()

def criar_icone():
    image = Image.open("CloudPOPBackup.png")    

    menu = Menu(
        MenuItem('Abrir', abrir_janela),
        MenuItem('Sair', sair)
    )
    icon = Icon("BackupApp", image, menu=menu)
    icon.title = "bkpCloudPOP - Sistema de Backup"
    icon.run()    
    

def sair(icon):    
    if janela == None:
        criar_janela()
    janela.withdraw()
    icon.stop()
    janela.quit()
    janela.destroy()

# Janela principal
def criar_janela():
    global origem_var, destino_var, horario_var, semana_vars, janela

    janela = tk.Tk()
    janela.title("bkpCloudPOP - Configuração de Backup")
    icone = PhotoImage(file="CloudPOPBackup.png")
    janela.iconphoto(True, icone)
    janela.geometry("600x380")
    versao = tk.Label(janela, text="Versão 1.0.0", font=("Arial", 9))
    versao.pack(pady=5, side="bottom", anchor="e")

    origem_var = tk.StringVar()
    destino_var = tk.StringVar()
    horario_var = tk.StringVar()

    # Pasta de Origem
    tk.Label(janela, text="Pasta de Origem:").pack(pady=5)
    frame_origem = tk.Frame(janela)
    frame_origem.pack(pady=5)
    tk.Entry(frame_origem, textvariable=origem_var, state="readonly", width=40, font=("Arial", 12)).pack(side="left", padx=5)
    tk.Button(frame_origem, text="Selecionar Origem", command=selecionar_origem).pack(side="left", padx=5)

    # Pasta de Destino
    tk.Label(janela, text="Pasta de Destino:").pack(pady=5)
    frame_destino = tk.Frame(janela)
    frame_destino.pack(pady=5)
    tk.Entry(frame_destino, textvariable=destino_var, state="readonly", width=40, font=("Arial", 12)).pack(side="left", padx=5)
    tk.Button(frame_destino, text="Selecionar Destino", command=selecionar_destino).pack(side="left", padx=5)

    # Horário
    tk.Label(janela, text="Horário (HH:MM):").pack(pady=5)
    frame_horario = tk.Frame(janela)
    frame_horario.pack(pady=5)
    entry_horario = tk.Entry(frame_horario, textvariable=horario_var, width=10, font=("Arial", 12))
    entry_horario.pack(side="left", padx=5)
    # Vincular evento para aplicar a máscara
    entry_horario.bind("<KeyRelease>", aplicar_mascara_horario)

    # Checkboxes para os dias da semana
    semana_vars = []
    dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

    # Criar um frame para agrupar os checkboxes
    frame_semana = tk.Frame(janela)
    tk.Label(janela, text="Dias da Semana:").pack(pady=5)
    frame_semana.pack(pady=5)
    for dia in dias:
        var = tk.BooleanVar()
        semana_vars.append(var)
        tk.Checkbutton(frame_semana, text=dia, variable=var).pack(side="left", padx=5)

    # Criar um frame para agrupar os botões
    frame_botoes = tk.Frame(janela)
    frame_botoes.pack(pady=25)

    # Botão de agendamento
    tk.Button(frame_botoes, text="Salvar/Agendar Backup", command=lambda: [agendar_backup(), salvar_configuracoes()]).pack(side="left", padx=20)
    tk.Button(frame_botoes, text="Executar Backup Agora", command=backup_imediato).pack(side="left", padx=10)

    # Remover o botão de fechar e minimizar para a bandeja
    janela.bind("<Unmap>", lambda event: janela.withdraw() if janela.state() == 'iconic' else None)
    janela.protocol("WM_DELETE_WINDOW", lambda: None)

    carregar_configuracoes()
    janela.mainloop()


# Iniciar a aplicação
if __name__ == "__main__":
    # Rodar o agendamento em uma thread separada
    threading.Thread(target=rodar_agendamentos, daemon=True).start()
    criar_icone()


