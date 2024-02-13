from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')
client = MongoClient(f"mongodb://{mongodb_username}:{mongodb_password}@localhost")


print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

def db_get_count():
    return  db.songs.count_documents({})

def db_get_song(song_id):
    song_id = int(song_id)
    song = db.songs.find_one({"id":song_id})
    if(not song):
        return False
    return song

    

@app.route("/health" , methods=["GET"])
def get_health():
    return {"status":"OK"}

@app.route("/count" , methods=["GET"])
def get_count():
    count = db_get_count()
    return {"count": count}


@app.route("/song" , methods=["GET"])
def songs():
    songs = json_util.dumps(list(db.songs.find({})))
    return {"songs":songs}

@app.route("/song" , methods=["POST"])
def create_song():
    data = request.get_json()
    song_id = data["id"]
    if(db_get_song(song_id)):
        return {"Message" : f"song with id {song_id} already present"} , 302
    lyrics = data["lyrics"]
    title = data["title"]
    ins_id = db.songs.insert_one({"lyrics":lyrics , "title":title , "id" : int(song_id)})
    return {"inserted id":{"$oid":json_util.dumps(ins_id.inserted_id)}} , 201

@app.route("/song/<song_id>" , methods=["GET"])
def get_song(song_id):
    song = db_get_song(song_id)
    
    if(not song):
        return {"status":"not found"}, 404

    return json_util.dumps(song), 200

@app.route("/song/<song_id>" , methods=["PUT"])
def update_song(song_id):
    song = db_get_song(song_id)
    if(not song):
        return {"message":"song not found"} , 404
    
    data = request.get_json()
    lyrics = data["lyrics"]
    title = data["title"]

    if(song["lyrics"]== lyrics and song["title"] == title):
        return {"message":"song found, but nothing updated"} , 200

    result = db.songs.update_one({"id":int(song_id)} ,{"$set":{"title":title , "lyrics":lyrics}})
    print(result.matched_count)
    song = db_get_song(song_id)
    return json_util.dumps(song),201

    

@app.route("/song/<song_id>" , methods=["DELETE"])
def delete_song(song_id):
    if(not db_get_song(song_id)):
        return {"message":"song not found"}, 404

    result = db.songs.delete_one({"id":int(song_id)})
    if(result.deleted_count < 1):
        return {"message":"nothing deleted"} , 404

    return {}, 204
    
