import requests
import psycopg2
import json
from dotenv import dotenv_values

dbconfig = dotenv_values(".env")

user= dbconfig['DBUSER']
password= dbconfig['DBPASSWORD']
host= dbconfig['DBHOST']
dbname= dbconfig['DBNAME']
port= dbconfig['DBPORT']
srid_target = dbconfig['SRID_TARGET']

connection_string = f"dbname='{dbname}' user='{user}' host='{host}' password='{password}'"

conn = psycopg2.connect(connection_string)
conn.autocommit = True
cur = conn.cursor()

localizacao = input("Informe a cidade onde deseja importar as rotas de ônibus: ")
print(localizacao)

prefixo_nominatim = 'https://nominatim.openstreetmap.org/search?q=' 
prefixo_overpass = 'http://overpass-api.de/api/interpreter?data='

url_nominatim = prefixo_nominatim + localizacao + '&format=json'
print(url_nominatim)
requisicao = requests.get(url_nominatim)
result_json = requisicao.json()

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

query_string = '[out:json];area(3600'+str(resultados[opcao]['osm_id'])+')->.searchArea;(relation["route"~"bus"](area.searchArea););out body geom;'

#print(query_string)

string_overpass = prefixo_overpass +query_string
#print(string_overpass)

print('Importando do OSM rotas de ônibus...')
rq = requests.get(string_overpass)

rotas_json = rq.json()

with open('rotas.json', 'w') as f:
    json.dump(rotas_json, f)

cont_rota = 0
cont_segmento = 0
rotas = []
rotas_vias = []
rotas_paradas = []

cont_erros = 0
erros = []

for rota in rotas_json['elements']:
    id_rota = rota['id']
    nome_rota = rota['tags']['name'] if 'name' in rota['tags'] else ''
    nome_rota = nome_rota.replace("'", "''")
    origem_rota = rota['tags']['from'] if 'from' in rota['tags'] else ''
    destino_rota = rota['tags']['to'] if 'to' in rota ['tags'] else ''
    tarifa_rota = rota['tags']['charge'] if 'charge' in rota['tags'] else ''
    rotas.append([id_rota,nome_rota,origem_rota,destino_rota,tarifa_rota])
    sequencia_paradas = 0
    sequencia_segmentos = 0
    for membro in rota['members']:
        if(membro['role'] == 'platform'):
            rotas_paradas.append([id_rota,sequencia_paradas, membro['ref']])
            sequencia_paradas+=1
        if(membro['role'] in ['', 'forward', 'backward']):
            rotas_vias.append([id_rota,sequencia_segmentos, membro['ref']])
            sequencia_segmentos+=1

with conn:
    print('Criando tabelas...')
    cur.execute("DROP TABLE IF EXISTS rotas")
    cur.execute("DROP TABLE IF EXISTS rotas_vias")
    cur.execute("DROP TABLE IF EXISTS rotas_paradas")
    cur.execute("COMMIT")
    try:
        cur.execute("CREATE TABLE rotas(id serial primary key, osmid_rota varchar(25), nome_rota text, origem_rota text, destino_rota text, tarifa_rota text)")
        cur.execute("CREATE TABLE rotas_vias(id serial primary key, osmid_rota varchar(25), sequencia integer, osmid_via varchar(25))")
        cur.execute("CREATE TABLE rotas_paradas(id serial primary key, osmid_rota varchar(25), sequencia integer, osmid_parada varchar(25))")
        cur.execute("COMMIT")
    except Exception as excep:
        erros.append(excep)
        cont_erros += 1
    cur.execute("COMMIT")


with conn:
    print('Inserindo registros da tabela "rotas"')
    for rota in rotas:
        insert_string = f"INSERT INTO rotas(osmid_rota, nome_rota, origem_rota, destino_rota, tarifa_rota) VALUES ('{rota[0]}', '{rota[1]}', '{rota[2]}', '{rota[3]}', '{rota[4]}')"
        #print(insert_string)
        try:
            cur.execute(insert_string)
        except Exception as excep:
            erros.append(excep)
            cont_erros += 1
        cur.execute("COMMIT")

    print('Inserindo registros da tabela "rotas_vias"')
    for rota_via in rotas_vias:
        insert_string = f"INSERT INTO rotas_vias(osmid_rota, sequencia, osmid_via) VALUES ('{rota_via[0]}', '{rota_via[1]}', '{rota_via[2]}')"
       #print(insert_string)
        try:
            cur.execute(insert_string)
        except Exception as excep:
            errox.append(excep)
            cont_erros += 1
        cur.execute("COMMIT")

### PARADAS DE ÔNIBUS ###
print('Importando do OSM paradas de ônibus...')

platforms_query_string = '[out:json];area(3600'+str(resultados[opcao]['osm_id'])+')->.searchArea;(way["public_transport"~"platform"](area.searchArea);node["public_transport"~"platform"](area.searchArea););out body geom;'
#print(query_string)
platforms_string_overpass = prefixo_overpass + platforms_query_string
print(platforms_string_overpass)
rq = requests.get(platforms_string_overpass)

platforms_json = rq.json()

with open('platforms.json', 'w') as f:
    json.dump(platforms_json, f)

lista_paradas = []
cont_erros = 0
erros = []

for parada in platforms_json['elements']:
    geometria = ''
    id_parada = parada['id']
    bench = parada['tags']['bench'] if 'bench' in parada['tags'] else ''
    shelter = parada['tags']['shelter'] if 'shelter' in parada['tags'] else ''
    name = parada['tags']['name'] if 'name' in parada['tags'] else ''
    if parada['type'] == 'node':
        geometria = f"ST_SetSRID(ST_GeomFromText('POINT({parada['lon']} {parada['lat']})'),4326)"
        lista_paradas.append([id_parada, name, bench, shelter, geometria])
    elif parada['type']  == 'way':
        pontos = parada['geometry']
        pontos_que_compoem = []
        for ponto in pontos: 
            pontos_que_compoem.append(f"{ponto['lon']} {ponto['lat']}")
        if(len(pontos_que_compoem) == 2): # mínimo de 3 pontos para formar um polígono
            geometria_parada = f"ST_Centroid(ST_SetSRID(ST_GeomFromText('LINESTRING({pontos_que_compoem[0]}, {pontos_que_compoem[1]})'), 4326))"
        else:
            pontos_que_compoem.append(pontos_que_compoem[0])
            pontos_sep_virgula = ','.join(pontos_que_compoem)
            pontos_text = f"POLYGON(({pontos_sep_virgula}))"
            geometria_parada = f"ST_Centroid(ST_SetSRID(ST_GeomFromText('{pontos_text}'), 4326))"
        lista_paradas.append([id_parada, name, bench, shelter, geometria_parada])

print(cont_erros)
print(erros)

with conn:
    print("Criando tabela de paradas...")
    cur.execute("DROP TABLE IF EXISTS paradas")
    cur.execute("CREATE TABLE paradas(id serial primary key, osmid varchar(50), name varchar(100), shelter varchar(50), bench varchar(50))")
    cur.execute("COMMIT")
    cur.execute("SELECT AddGeometryColumn ('public','paradas','geom_4326',4326,'POINT',2)")
    cur.execute(f"SELECT AddGeometryColumn ('public','paradas','geom_{srid_target}',{srid_target},'POINT',2)")
    cur.execute("COMMIT")
    print('Inserindo registros na tabela "paradas"')
    for parada in lista_paradas:
        insert_string = f"INSERT INTO paradas(osmid, name, bench, shelter, geom_4326) VALUES ( '{parada[0]}', '{parada[1]}', '{parada[2]}',  '{parada[3]}', {parada[4]})"
        #print(insert_string)
        try:
            cur.execute(insert_string)
        except:
            cont_erros+=1
            erros.append(insert_string)
        cur.execute("COMMIT")

print(cont_erros)
print(erros)

cont_erros = 0
erros = []

with conn:
    print('Inserindo registros na tabela "rotas_paradas"')
    for rota_parada in rotas_paradas:
        insert_string = f"INSERT INTO rotas_paradas(osmid_rota, sequencia, osmid_parada) VALUES ('{rota_parada[0]}', {rota_parada[1]}, '{rota_parada[2]}')"
        #print(insert_string)
        try:
            cur.execute(insert_string)
        except Exception as excep:
            erros.append(excep)
            cont_erros += 1
        reprojetar_string = f'UPDATE paradas set geom_{srid_target} = ST_Transform(geom_4326, {srid_target})'
        try:
            cur.execute(reprojetar_string)
        except Exception as excep:
            erros.append(excep)
            cont_erros += 1
        cur.execute("COMMIT")

print(cont_erros)
print(erros)
