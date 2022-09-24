# OSMBUS2PGR

## Ferramenta escrita em Python para importação de rede viária e rotas de ônibus de uma cidade a partir de dados do OpenStreetMap para o banco de dados PostgreSQL com as extensões PostGIS e pgRouting. 

### Extração de Sistema Viário
* Busca no Nominatim a cidade informada pelo usuário
* Faz o download da rede viária em toda a extensão da cidade
* Segmenta todas as linhas de n vértices em n-1 linhas de 2 vértices (origem e destino do arco)
* Cria as extensões, tabelas e colunas necessárias no banco
* Preenche as colunas de custo e custo no sentido oposto da via
* Cria a topologia de rede utilizando a função pgr_createTopology do pgRouting

### Extração de Rotas
* Busca no Nominatim a cidade informada pelo usuário
* Faz o download de todas as "relations" de rotas de ônibus na extensão da cidade (inclusive intermunicipais)
* Cria tabelas rotas, rotas_vias e rotas_paradas no banco
* Faz o preenchimento das tabelas a partir do processamento dos dados obtidos do OpenStreetMap

Testado com:
- Python 3.9.2
- PostgreSQL 14
- PostGIS 3.2.2
- pgRouting 3.3.0
