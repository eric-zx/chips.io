# Sistema de Monitoramento de Chips

Sistema completo para monitoramento de chips SIM (identificados por ICCID), com controle de entrada, saída, cadastro em lote e individual, e registro de retiradas.

## Funcionalidades

### ✅ Cadastro Individual
- Cadastro de chips um por vez
- Identificação por ICCID
- Seleção de operadora (Claro, Tim, Arquia, Quectel Tim, Quectel Vivo, Vivo)
- Campo de observações

### ✅ Cadastro em Lote
- Cadastro de múltiplos chips de uma vez
- Criação de remessas com número gerado automaticamente
- Importação de arquivos CSV ou XLSX
- Formato: ICCID,Operadora (um por linha)
- Número de remessa único: REM-YYYYMMDD-NNNN (gerado automaticamente)

### ✅ Retirada de Chips
- Busca de chip por ICCID
- Registro de quem retirou o chip
- Data e hora da retirada
- Validação de disponibilidade

### ✅ Consulta de Chips
- Listagem de todos os chips
- Filtros por operadora e status
- Exportação para CSV
- Visualização de informações completas

### ✅ Gestão de Remessas
- Histórico de todas as remessas
- Informações detalhadas de cada remessa
- Quantidade de chips por remessa

### ✅ Estatísticas
- Total de chips cadastrados
- Chips disponíveis
- Chips retirados
- Total de remessas

## Requisitos

- Python 3.6 ou superior
- Bibliotecas padrão (tkinter, sqlite3) - já incluídas no Python
- **Opcional**: `openpyxl` para importação de arquivos XLSX
  ```bash
  pip install openpyxl
  ```

## Como usar

1. Execute o arquivo `monitoramento.py`:
   ```bash
   python monitoramento.py
   ```

2. O banco de dados será criado automaticamente (`chips.db`) na primeira execução

3. Use as abas para navegar entre as funcionalidades:
   - **Cadastro Individual**: Para cadastrar chips um por vez
   - **Cadastro em Lote**: Para cadastrar múltiplos chips e criar remessas
   - **Retirada de Chip**: Para registrar a saída de chips
   - **Consulta de Chips**: Para visualizar e filtrar chips
   - **Remessas**: Para ver o histórico de remessas
   - **Estatísticas**: Para ver estatísticas gerais

## Operadoras Suportadas

- Claro
- Tim
- Arquia
- Quectel Tim
- Quectel Vivo
- Vivo

## Formato de Importação (CSV ou XLSX)

### Arquivo CSV
O arquivo CSV deve ter o formato:
```csv
ICCID1,Operadora1
ICCID2,Operadora2
ICCID3,Operadora3
```

Exemplo:
```csv
89550000000000000001,Claro
89550000000000000002,Tim
89550000000000000003,Vivo
```

### Arquivo XLSX (Excel)
O arquivo XLSX deve ter o mesmo formato em uma planilha:
- Coluna A: ICCID
- Coluna B: Operadora
- A primeira linha pode conter cabeçalhos (será ignorada)

**Nota**: Para importar arquivos XLSX, instale a biblioteca `openpyxl`:
```bash
pip install openpyxl
```

## Geração Automática de Números de Remessa

O sistema gera automaticamente números de remessa únicos no formato:
- `REM-YYYYMMDD-NNNN`
- Exemplo: `REM-20240115-0001`, `REM-20240115-0002`, etc.

Os números são gerados automaticamente e garantem unicidade, evitando colisões. Cada dia começa com o número 0001.

## Banco de Dados

O sistema utiliza SQLite e cria automaticamente as tabelas:
- `chips`: Armazena informações dos chips
- `remessas`: Armazena informações das remessas

O arquivo `chips.db` será criado na mesma pasta do script.
