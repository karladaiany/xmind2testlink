import sys
import os
from xmind2testlink.web.custom_converter import custom_xmind_to_testlink

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 run_converter.py <caminho_arquivo_entrada.xmind>")
        sys.exit(1)
        
    input_path = sys.argv[1]
    
    # A função custom_xmind_to_testlink já faz todo o pipeline de 3 passos
    # e retorna o caminho do XML final.
    custom_xmind_to_testlink(input_path)
