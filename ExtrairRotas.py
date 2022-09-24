import requests
import psycopg2
import json
from dotenv import dotenv_values
#import sys

dbconfig = dotenv_values(".env")

user= dbconfig['DBUSER']
password= dbconfig['DBPASSWORD']
host= dbconfig['DBHOST']
dbname= dbconfig['DBNAME']
port= dbconfig['DBPORT']

#print(user)
#print(password)
#print(host)
#print(dbname)
#print(port)
#sys.exit()

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
#api.query(query_string)
#print(query_string)

string_overpass = prefixo_overpass +query_string
print(string_overpass)
rq = requests.get(string_overpass)

rotas_json = rq.json()
with open('rotas.json', 'w') as f:
    json.dump(rotas_json, f)
# parse file
#rotas_json = json.loads(dados)

cont_rota = 0
cont_segmento = 0
rotas = []
rotas_vias = []
rotas_paradas = []

for rota in rotas_json['elements']:
    id_rota = rota['id']
    nome_rota = rota['tags']['name']
    origem_rota = rota['tags']['from'] if 'from' in rota['tags'] else ''
    destino_rota = rota['tags']['to'] if 'to' in rota ['tags'] else ''
    tarifa_rota = rota['tags']['charge'] if 'charge' in rota['tags'] else ''
    rotas.append([id_rota,nome_rota,origem_rota,destino_rota,tarifa_rota])
    sequencia_paradas = 0
    sequencia_segmentos = 0
    for membro in rota['members']:
        if(membro['role'] == 'platform'):
            rotas_paradas.append([id_rota,sequencia_paradas,membro['ref']])
            sequencia_paradas+=1
        if(membro['role'] == ''):
            rotas_vias.append([id_rota,sequencia_segmentos,membro['ref']])
            sequencia_segmentos+=1

with conn:
    cur.execute("DROP TABLE IF EXISTS rotas")
    cur.execute("DROP TABLE IF EXISTS rotas_vias")
    cur.execute("DROP TABLE IF EXISTS rotas_paradas")
    cur.execute("COMMIT")
    try:
        cur.execute("CREATE TABLE rotas(id serial primary key, osmid_rota varchar(25), nome_rota varchar(50), origem_rota varchar(25), destino_rota varchar(25), tarifa_rota varchar(25))")
        cur.execute("CREATE TABLE rotas_vias(id serial primary key, osmid_rota varchar(25), sequencia integer, osmid_via varchar(25))")
        cur.execute("CREATE TABLE rotas_paradas(id serial primary key, osmid_rota varchar(25), sequencia integer, osmid_parada varchar(25))")
        cur.execute("COMMIT")
    except Exception as excep:
        print(excep)

    for rota in rotas:
        insert_string = f"INSERT INTO rotas(osmid_rota, nome_rota, origem_rota, destino_rota, tarifa_rota) VALUES ('{rota[0]}', '{rota[1]}', '{rota[2]}', '{rota[3]}', '{rota[4]}')"
        print(insert_string)
        cur.execute(insert_string)
    cur.execute("COMMIT")

    for rota_via in rotas_vias:

        insert_string = f"INSERT INTO rotas_vias(osmid_rota, sequencia, osmid_via) VALUES ('{rota_via[0]}', '{rota_via[1]}', '{rota_via[2]}')"
        print(insert_string)
        cur.execute(insert_string)
    cur.execute("COMMIT")

    for rota_parada in rotas_paradas:
        insert_string = f"INSERT INTO rotas_paradas(osmid_rota, sequencia, osmid_parada) VALUES ('{rota_parada[0]}', {rota_parada[1]}, '{rota_parada[2]}')"
        print(insert_string)
        cur.execute(insert_string)
    cur.execute("COMMIT")

   
