import os,re,json
import aprslib
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def dms2dec(dms_str):    
    dms_str = re.sub(r'\s', '', dms_str)
    
    sign = -1 if re.search('[swSW]', dms_str) else 1
    
    numbers = [*filter(len, re.split('\D+', dms_str, maxsplit=4))]

    degree = numbers[0]
    minute = numbers[1] if len(numbers) >= 2 else '0'
    second = numbers[2] if len(numbers) >= 3 else '0'
    frac_seconds = numbers[3] if len(numbers) >= 4 else '0'
    
    second += "." + frac_seconds
    return sign * (int(degree) + float(minute) / 60 + float(second) / 3600)

def getGPSLocation(indicative):
    url = 'https://aprs.fi/info/a/{0}'.format(indicative)

    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')

    dec = re.compile(r"^-?[0-9]\d*\.\d+?")
    for tr in soup.find_all('tr'):
        th = tr.find('th')
        if th.string == 'Location:':
            td = tr.find('td').text
            location = td.split('-')
            tmp = re.findall("[0-9]+°[0-9]+.[0-9]+'.?[WESN]", location[0])
            return dms2dec(tmp[0]), dms2dec(tmp[1])

def touchJsonFile(filepath):
    if not os.path.exists(filepath):
        f = open(filepath, 'a')
        f.write(json.dumps([]))
        f.close()

filename = "file_to_parse.txt"
jsonFolder = "json/"
objOutput = []
i = 0
objListener = set()
day = ''
filenames= []
positionJson = jsonFolder+'positions.json'
relaysJson = jsonFolder+'relays.json'

# checking if positions.json and relays.json are existing, if not creating them
touchJsonFile(positionJson)
touchJsonFile(relaysJson)

with open(filename) as file:
    for line in file:
        new = re.findall(r'(.*)CEST: (.*)', line.rstrip())
        if day != '' and day != new[0][0][0:10]:
            fileday = "{0}.json".format(day)
            filenames.append(fileday)
            f = open(jsonFolder+fileday, "w")
            f.write(json.dumps(objOutput))
            f.close()
            print("{0} created".format(fileday))
            objOutput = []

        aprs_details = None
        try:
            aprs_details = aprslib.parse(new[0][1])
        except aprslib.exceptions.ParseError as e:
            print(f"Error: {e.message}")
            print(f"On Line: {new[0][1]}")

        if aprs_details:
            for k in range(0, len(aprs_details['path'])):
                if not re.match('WIDE', aprs_details['path'][k]) and not re.match('qAR', aprs_details['path'][k]):
                    listener = aprs_details['path'][k].split('*')
                    break
            
            objOutput.append({
                "id":i, 
                "lat":aprs_details['latitude'], 
                "lon":aprs_details['longitude'], 
                "listener":listener[0],
                "symbol": aprs_details['symbol'],
                "symbol_table": aprs_details['symbol_table'],
                "time": new[0][0]
            })
            objListener.add(listener[0])
            i = i+1
            day = new[0][0][0:10]

fileday = "{0}.json".format(day)
filenames.append(fileday)
f = open(jsonFolder+fileday, "w")
f.write(json.dumps(objOutput))
f.close()
print("{0} created".format(fileday))


print("{0} traces added".format(i))

with open(positionJson, 'r') as file:
    data = file.read().replace('\n', '')
objFiles = json.loads(data)
for fileday in objFiles:
    if fileday in filenames:
        filenames.remove(fileday)
objFiles.extend(filenames)

f = open(positionJson, "w")
f.write(json.dumps(objFiles))
f.close()

with open(relaysJson, 'r') as file:
    data = file.read().replace('\n', '')

objRelays = json.loads(data)
for relay in objRelays:
    if relay['indicative'] in objListener:
        objListener.remove(relay['indicative'])

if len(objListener) == 0:
    print("No relay to add")
else:
    for indicative in objListener:
        print("looking for relay {0}".format(indicative))
        lat, lon = getGPSLocation(indicative)
        objRelays.append({"indicative": indicative, "lon": lon, "lat": lat})
        print("Adding relay {0}".format(indicative))

f = open(relaysJson, "w")
f.write(json.dumps(objRelays))
f.close()

os.rename(filename, 'archives/{0}.txt'.format(datetime.today().strftime('%Y-%m-%d')))