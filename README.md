# osmbus2pgr

Ferramenta desenvolvida com [Python](https://python.org) para importação de rede viária e rotas de ônibus de uma cidade a partir de dados do [OpenStreetMap](https://openstreetmap.org) para o banco de dados [PostgreSQL](https://www.postgresql.org/) com as extensões [PostGIS](https://postgis.net) e [pgRouting](https://pgrouting.org). 

Baseada no trabalho final apresentado por mim da disciplina de Programação de Computadores Aplicada a Transportes, ministrada pelo professor [Alexandre Hering Coelho](https://ahcoelho.paginas.ufsc.br/) no Programa de Pós-Graduação em Engenharia de Transpotes e Gestão Territoral ([PPGTG](https://ppgtg.ufsc.br)) da Universidade Federal de Santa Catarina ([UFSC](https://ufsc.br)). 

### Extração de Sistema Viário
* Busca no [Nominatim](https://nominatim.openstreetmap.org/) a cidade informada pelo usuário
* Faz o download a partir do OpenStreetMap da rede viária em toda a extensão da cidade
* Segmenta todas as linhas de n vértices em n-1 linhas de 2 vértices (origem e destino do arco)
* Cria as extensões, tabelas e colunas necessárias no banco
* Preenche as colunas de custo e custo no sentido oposto da via
* Cria a topologia de rede utilizando a função [pgr_createTopology](https://docs.pgrouting.org/3.3/en/pgr_createTopology.html) do pgRouting

### Extração de Rotas
* Busca no Nominatim a cidade informada pelo usuário
* Faz o download de todas as [relations](https://wiki.openstreetmap.org/wiki/Relation:route) de rotas de ônibus na extensão da cidade (inclusive rotas intermunicipais)
* Cria tabelas rotas, rotas_vias e rotas_paradas no banco
* Preenche as tabelas a partir do processamento dos dados obtidos do OpenStreetMap

## Testado com:
- Python 3.9.2
- PostgreSQL 14
- PostGIS 3.2.2
- pgRouting 3.3.0

## Dependências:
- [requests](https://pypi.org/project/requests/)
- [psycopg2](https://pypi.org/project/psycopg2/)
- [dotenv](https://pypi.org/project/dotenv/)

## Como usar:
1) Crie um banco no PostgreSQL com o nome de sua preferência.
2) Garanta que você está com as extensões PostGIS e pgRouting instaladas nas versões testadas:
```
CREATE EXTENSION postgis;
CREATE EXTENSION pgrouting;
```
3) Edite o arquivo .env com as configurações do seu banco e com SRID apropriado para a cidade escolhida
4) Execute o arquivo ExtrairSistemaViario.py
```
python3 ExtrairSistemaViario.py
```
5) Execute o arquivo ExtrairRotas.py
```
python3 ExtrairRotas.py
```
## Como consultar informações sobre rotas?
### Quais as rotas foram importadas?
```
select * from rotas;
```

### Qual o trajeto de uma rota específica?
```
SELECT rotas_vias.sequencia, vias.osmid, ST_LineMerge(ST_Union(vias.geom))
FROM rotas JOIN rotas_vias ON rotas.osmid_rota = rotas_vias.osmid_rota JOIN vias ON rotas_vias.osmid_via = vias.osmid 
WHERE nome_rota ilike '%circular - bairro%'
GROUP BY rotas_vias.sequencia, vias.osmid 
ORDER BY rotas_vias.sequencia
```
(É possível visualizar a geometria no mapa embutido do pgAdmin ou do dBeaver, ou executando a consulta dentro do QGIS)
