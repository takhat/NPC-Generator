import os
from flask import Blueprint, jsonify, request, abort, make_response
from ..db import db
from ..models.character import Character
from ..models.greeting import Greeting
from sqlalchemy import func, union, except_
from openai import OpenAI

client = OpenAI(
api_key = os.environ.get("LLAMA_API_KEY"),
base_url = "https://api.llama-api.com"
)

bp = Blueprint("characters", __name__, url_prefix="/characters")

@bp.post("")
def create_character():

    request_body = request.get_json()
    try: 
        new_character = Character.from_dict(request_body)
        db.session.add(new_character)
        db.session.commit()

        return make_response(new_character.to_dict(), 201)
    
    except KeyError as e:
        abort(make_response({"message": f"missing required value: {e}"}, 400))

@bp.get("")
def get_characters():
    character_query = db.select(Character)

    characters = db.session.scalars(character_query)
    response = []

    for character in characters:
        response.append(
            {
                "id" : character.id,
                "name" : character.name,
                "personality" : character.personality,
                "occupation" : character.occupation,
                "age" : character.age
            }
        )

    return jsonify(response)

@bp.get("/<char_id>/greetings")
def get_greetings(char_id):
    character=validate_model(Character,char_id)
    if not character.greetings:
        return make_response(
            jsonify(
                f"No greetings found for {character.name}"), 201)

@bp.post("/<char_id>/generate")
def add_greetings(char_id):
    character=validate_model(Character,char_id)
    greetings=generate_greeting(character)
    if character.greetings:
        return make_response(
            jsonify(f"Greetings already exist for {character.name}"), 201)     
    new_greetings = []
    for greeting in greetings:
        new_greeting = Greeting(
            greeting_text = greeting[greeting.find(" ")+1:].strip("\""),
            character = character
        )
        new_greetings.append(new_greeting)
        db.session.add_all(new_greetings)
        db.session.commit()
        return make_response(jsonify(f"Greetings successfully added to {character.name}"), 201)
def generate_greeting(character):
    prompt = f"I am writing a fantasy style role playing video game. I have an npc named {character.name} who is {character.age}.They are a {character.occupation} who has a {character.personality} personality. Can you help me python style list of 10 stock phrases they might use when another character talks to them?"
    response = client.chat.completions.create(
        # model="gpt-3.5-turbo",
        model="llama-13b-chat",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.split("\n")

def validate_model(cls,id):
    try:
        id = int(id)
    except:
        response =  response = {"message": f"{cls.__name__} {id} invalid"}
        abort(make_response(response , 400))

    query = db.select(cls).where(cls.id == id)
    model = db.session.scalar(query)
    if model:
        return model

    response = {"message": f"{cls.__name__} {id} not found"}
    abort(make_response(response, 404))