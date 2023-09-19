import json
import requests
import psycopg2
from dotenv import dotenv_values
import sys

config = dotenv_values(".env")

user= config['DBUSER']
password= config['DBPASSWORD']
host= config['DBHOST']
dbname= config['DBNAME']
port= config['DBPORT']
srid_target = config['SRID_TARGET']

#print(user)
#print(password)
#print(host)
#print(dbname)
#print(port)
#print(srid_target)
#sys.exit()

connection_string = f"dbname='{dbname}' user='{user}' host='{host}' password='{password}'"

conn = psycopg2.connect(connection_string)
conn.autocommit = True
cur = conn.cursor()

localizacao = input("Informe a cidade onde deseja importar sistema viário: ")

prefixo_nominatim = 'https://nominatim.openstreetmap.org/search?q=' 
prefixo_overpass = 'http://overpass-api.de/api/interpreter?data='

url_nominatim = prefixo_nominatim + localizacao + '&format=json'

requisicao = requests.get(url_nominatim)
result_json = requisicao.json()
if(not result_json):
    print("Sem resultados. Encerrando...")
    sys.exit()
resultados = []
contador = 0
for result in result_json:
    resultado = {}
    resultado['indice'] = contador
    resultado['osm_id'] = result['osm_id']
    resultado['nome'] = result['display_name']
    resultado['tag'] = result['class']
    resultado['valor'] = result['type']
    resultados.append(resultado)
    contador+=1

for resultado in resultados:
    print(str(resultado['indice']) + ' - ' + resultado['nome'])

opcao = int(input("Informe o número da opção desejada: "))

query_string = '[out:json];area(3600'+str(resultados[opcao]['osm_id'])+')->.searchArea;(way["highway"~"motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|residential|service|living_street|busway|road|unclassified"](area.searchArea););out body geom;'
#api.query(query_string)
#print(query_string)

string_overpass = prefixo_overpass +query_string
#print(string_overpass)
print("\nObtendo dados do OpenStreetMap...")
rq = requests.get(string_overpass)
sistema_viario_json = rq.json()

#ruas_explodidas = [['highway','osm_id','name','surface','max_speed','one_way','geom']]
ruas_explodidas = []

for way in sistema_viario_json['elements']:
    highway = way['tags']['highway']
    osm_id = way['id']
    name = way['tags']['name'] if 'name' in way['tags'] else ""
    surface = way['tags']['surface'] if 'surface' in way['tags'] else ""
    maxspeed = way['tags']['maxspeed'] if 'maxspeed' in way['tags'] else ""
    oneway = way['tags']['oneway'] if 'oneway' in way['tags'] else ""
    geometria = []

    for geometry in way['geometry']:
        geometria.append( (geometry['lon'], geometry['lat']) )

    for i in range(len(geometria)-1):
        linha = f'LINESTRING({geometria[i][0]} {geometria[i][1]}, {geometria[i+1][0]} {geometria[i+1][1]})'
        ruas_explodidas.append([highway,osm_id,name,surface,maxspeed,oneway,linha])

erros = []
cont_erros = 0
print(f"Criando o banco de dados de {localizacao}...")
with conn:
    cur.execute("DROP TABLE IF EXISTS vias")
    cur.execute("DROP TABLE IF EXISTS vias_vertices_pgr ")
    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    cur.execute("CREATE EXTENSION IF NOT EXISTS pgrouting")
    cur.execute("COMMIT")
    cur.execute("CREATE TABLE vias(id serial primary key,highway varchar(50), osmid varchar(50), name varchar(100), surface varchar(50), maxspeed varchar(50), oneway varchar(50))")
    cur.execute("COMMIT")
    cur.execute("SELECT AddGeometryColumn ('public','vias','geom_4326',4326,'LINESTRING',2)")
    cur.execute(f"SELECT AddGeometryColumn ('public','vias','geom_{srid_target}',{srid_target},'LINESTRING',2)")
    cur.execute("COMMIT")
    for rua in ruas_explodidas:
        nome_rua = rua[2].replace("'","''")
        #nome_rua = nome_rua.replace("(","- ")
        #nome_rua = nome_rua.replace(")","")
        insert_string = f"INSERT INTO vias(highway,osmid,name,surface,maxspeed,oneway,geom_4326) VALUES ( '{rua[0]}', '{rua[1]}', '{nome_rua}',  '{rua[3]}', '{rua[4]}', '{rua[5]}', ST_GeomFromText('{rua[6]}',4326))"
        try:
            cur.execute(insert_string)
        except:
            cont_erros+=1
            erros.append(insert_string)
        cur.execute("COMMIT")
    
    #Reprojeção de coordenadas geográficas em graus para o sistema de coordenadas alvo (em metros)
    cur.execute(f"UPDATE vias SET geom_{srid_target} = ST_Transform(geom_4326,{srid_target})")
    cur.execute("COMMIT")

    #Criação de columas de custo, custo reverso e vértices de origem e destino
    cur.execute("ALTER TABLE vias ADD COLUMN cost real")
    cur.execute("ALTER TABLE vias ADD COLUMN reverse_cost real")
    cur.execute("ALTER TABLE vias ADD COLUMN source integer")
    cur.execute("ALTER TABLE vias ADD COLUMN target integer")
    cur.execute("COMMIT")

    #Criação de índices para as colunas de identificação e vértices origem/destino na tabela de vias
    cur.execute("CREATE INDEX vias_idx ON vias (id)")
    cur.execute("CREATE INDEX vias_source_idx ON vias (source)")
    cur.execute("CREATE INDEX vias_target_idx ON vias (target)")
    cur.execute("COMMIT")

    #Cálculo e preenchimento do custo e custo reverso baseados no comprimento da via
    cur.execute(f"UPDATE vias SET cost = ST_Length(geom_{srid_target}) / 1000")
    cur.execute("COMMIT")
    cur.execute("UPDATE vias SET reverse_cost = cost * -1.0")
    cur.execute("COMMIT")

    #Preenchimento de custo igual a -1 para vias de mão única
    cur.execute("UPDATE vias SET reverse_cost = -1 WHERE oneway = 'yes'")
    cur.execute("COMMIT")

    print("Criando topologia da malha viária...")
    cur.execute(f"SELECT pgr_createTopology('vias', 0.01, 'geom_{srid_target}','id')")
    cur.execute("COMMIT")

print(f'Quantidade de erros: {cont_erros}')
if cont_erros > 0:
    print(erros)

