import sys
import os

# Adiciona o diretório atual ao sys.path para importação local
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importa o custom_converter.py do mesmo diretório
from custom_converter import custom_xmind_to_testlink 

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 run_converter.py <caminho_arquivo_entrada.xmind>")
        sys.exit(1)
        
    input_path = sys.argv[1]
    
    # A função custom_xmind_to_testlink já faz todo o pipeline de 3 passos
    # e retorna o caminho do XML final.
    custom_xmind_to_testlink(input_path)
