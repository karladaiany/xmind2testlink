import os
import sys
import zipfile
import json
import re
import xml.etree.ElementTree as ET
from contextlib import closing
from os.path import join, exists

# Adiciona o diretório raiz do fork ao path para importar os scripts
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from xmind2testlink.main import xmind_to_testlink

# --- Funções de Pré-processamento (Adaptadas de preprocess_xmind.py) ---
PRECONDITIONS_TAG = "[PRECONDITIONS]"
TEMP_DIR = "/tmp/xmind_extract"

def process_topic(topic):
    """
    Processa um tópico, extraindo a pré-condição da nota e movendo-a para o comentário.
    """
    if 'notes' in topic and 'plain' in topic['notes'] and 'content' in topic['notes']['plain']:
        note_content = topic['notes']['plain']['content']
        
        # Expressão regular para encontrar a tag e o conteúdo subsequente
        match = re.search(r'\[PRECONDITIONS\]\s*(.*)', note_content, re.DOTALL | re.IGNORECASE)
        
        if match:
            # Conteúdo da pré-condição é o grupo de captura 1
            preconditions_content = match.group(1).strip()
            
            # Adiciona o conteúdo ao campo 'comments'
            topic['comments'] = preconditions_content
            
            # Remove a tag [PRECONDITIONS] e o conteúdo subsequente do campo 'notes'
            new_note_content = re.sub(r'\s*\[PRECONDITIONS\].*', '', note_content, flags=re.DOTALL | re.IGNORECASE).strip()
            
            if new_note_content:
                topic['notes']['plain']['content'] = new_note_content
                # Também limpa o realHTML se existir
                if 'realHTML' in topic['notes'] and 'content' in topic['notes']['realHTML']:
                    topic['notes']['realHTML']['content'] = re.sub(r'<br>\[PRECONDITIONS\].*', '', topic['notes']['realHTML']['content'], flags=re.DOTALL | re.IGNORECASE).strip()
            else:
                # Se a nota ficar vazia, remove o campo 'notes' para evitar resumo vazio
                del topic['notes']
    
    if 'children' in topic and 'attached' in topic['children']:
        for child_topic in topic['children']['attached']:
            process_topic(child_topic)

def preprocess_xmind(input_xmind_path, output_xmind_path):
    """
    Função principal para pré-processar o arquivo XMind.
    """
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    
    try:
        with zipfile.ZipFile(input_xmind_path, 'r') as zip_ref:
            zip_ref.extractall(TEMP_DIR)
    except Exception:
        return # Falha na descompactação

    content_json_path = os.path.join(TEMP_DIR, 'content.json')
    
    try:
        with open(content_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for sheet in data:
            if 'rootTopic' in sheet:
                process_topic(sheet['rootTopic'])
        
        with open(content_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
    except Exception:
        os.system(f"rm -rf {TEMP_DIR}")
        return # Falha no processamento do JSON

    try:
        with zipfile.ZipFile(output_xmind_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(TEMP_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, TEMP_DIR))
        
    except Exception:
        return # Falha na recompactação
    finally:
        os.system(f"rm -rf {TEMP_DIR}")

# --- Funções de Pós-processamento (Adaptadas de postprocess_xml.py) ---
def extract_comments_from_xmind(input_xmind_path):
    comments_map = {}
    
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    
    try:
        with zipfile.ZipFile(input_xmind_path, 'r') as zip_ref:
            zip_ref.extractall(TEMP_DIR)
    except Exception:
        return comments_map

    content_json_path = os.path.join(TEMP_DIR, 'content.json')

    def traverse_topics(topic):
        if 'title' in topic and 'comments' in topic:
            comments_map[topic['title']] = topic['comments']
        
        if 'children' in topic and 'attached' in topic['children']:
            for child_topic in topic['children']['attached']:
                traverse_topics(child_topic)

    try:
        with open(content_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for sheet in data:
            if 'rootTopic' in sheet:
                traverse_topics(sheet['rootTopic'])
        
    except Exception:
        pass

    os.system(f"rm -rf {TEMP_DIR}")
    
    return comments_map

def postprocess_xml(input_xml_path, input_xmind_path, output_xml_path):
    comments_map = extract_comments_from_xmind(input_xmind_path)
    
    if not comments_map:
        os.rename(input_xml_path, output_xml_path)
        return

    try:
        tree = ET.parse(input_xml_path)
        root = tree.getroot()
    except Exception:
        return

    for testsuite in root.findall('testsuite'):
        for testcase in testsuite.findall('testcase'):
            testcase_name = testcase.get('name')
            
            if testcase_name in comments_map:
                preconditions_text = comments_map[testcase_name]
                
                preconditions_element = testcase.find('preconditions')
                
                if preconditions_element is not None:
                    # Injeta o texto na tag <preconditions>
                    preconditions_element.text = preconditions_text

    try:
        # Salva o XML modificado
        tree.write(output_xml_path, encoding='utf-8', xml_declaration=True)
    except Exception:
        pass

# --- Função Principal do Pipeline ---
def custom_xmind_to_testlink(xmind_path):
    """
    Função que implementa o pipeline de 3 passos:
    1. Pré-processamento: Corrige o XMind para injetar o campo 'comments'.
    2. Conversão: Usa o xmind2testlink no arquivo corrigido.
    3. Pós-processamento: Corrige o XML gerado, injetando as pré-condições.
    """
    
    # 1. Pré-processamento
    corrigido_xmind_path = xmind_path.replace('.xmind', '_corrigido.xmind')
    preprocess_xmind(xmind_path, corrigido_xmind_path)
    
    # Se o pré-processamento falhou, usa o arquivo original
    if not os.path.exists(corrigido_xmind_path):
        corrigido_xmind_path = xmind_path
    
    # 2. Conversão (usando o xmind2testlink original no arquivo corrigido)
    xmind_to_testlink(corrigido_xmind_path)
    
    # O XML gerado terá o nome do arquivo corrigido, mas com extensão .xml
    corrigido_xml_path = corrigido_xmind_path.replace('.xmind', '.xml')
    final_xml_path = xmind_path.replace('.xmind', '.xml')
    
    # 3. Pós-processamento
    postprocess_xml(corrigido_xml_path, corrigido_xmind_path, final_xml_path)
    
    # 4. Limpeza: Remove os arquivos temporários, mantendo o final.xml
    if os.path.exists(corrigido_xmind_path) and corrigido_xmind_path != xmind_path:
        os.remove(corrigido_xmind_path)
    if os.path.exists(corrigido_xml_path):
        os.remove(corrigido_xml_path)

    # Retorna o caminho do arquivo final
    return final_xml_path