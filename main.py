from typing import Optional
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import openai
import dotenv
import os
import json

dotenv.load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


class WorldObject(BaseModel):
    name: str
    metadata: dict | None


class World(BaseModel):
    objects: list[WorldObject]


class RenderObjectResponse(BaseModel):
    html: str


class RenderObjectRequest(BaseModel):
    world: World
    object: WorldObject


def fix_model_output(output, start="{", end="}"):
    # Find the first { and the last }
    first_bracket = output.find(start)
    last_bracket = output.rfind(end)
    result = output[first_bracket : last_bracket + 1]
    print(result)
    return result


@app.get("/api/gen_world")
def gen_world(world_desc: str) -> World:
    try:
        result = (
            openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are WorldModelAI. Your purpose is to model"
                        " the game world as accurately as possible. The world is "
                        "represented as a JSON object that describes an "
                        "environment or scene. Objects do not have a position."
                        "The player must be an object of the world. There must"
                        "also be a game_state object that holds core variables"
                        "for the game loop. The game_state object must also have"
                        "a small description of the game and the player's goal or"
                        "win conditions."
                        "Here is an example world:"
                        '{"objects": [{"name": "tree", "metadata": {"color": "green"}},'
                        '{"name": "player", "metadata": {"has_axe": false}},'
                        '{"name": "game_state", "metadata": {"has_won": false, '
                        '"description": "You are a lumberjack. You must cut down the tree."}}]}'
                        "\n The name of each object must be unique. The metadata"
                        " can be any JSON object. Only output the JSON object.",
                    },
                    {"role": "user", "content": world_desc},
                ],
            )
            .choices[0]
            .message.content
        )
        result = fix_model_output(result)

        world_dict = json.loads(result)
        world = World.parse_obj(world_dict)

        return world
    except Exception as e:
        return gen_world(world_desc)


@app.post("/api/render_object")
def render_object(request: RenderObjectRequest) -> RenderObjectResponse:
    try:
        world, object = request.world, request.object
        result = (
            openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "user",
                        "content": "World context: " + json.dumps(world.dict()),
                    },
                    {
                        "role": "system",
                        "content": "You are WebGameRendererAI. Your purpose is to render"
                        " world objects as HTML for a web game. These renders must be"
                        " simple but charming and must represent the state of the object."
                        " Note that there are some metadata fields that should not be"
                        " rendered. "
                        "For example, you must not show the age of an NPC"
                        " that the player has not met yet."
                        "The object must be rendered as an HTML div and can use Tailwind css classes. "
                        "They can use the style attribute for css and hardcoded svg or such."
                        "\n Feel free to make your renders detailed, colorful, and artistic."
                        " Only output the HTML. Do not use images or other external assets."
                        " You must not use position: absolute, position: fixed"
                        " css. This is because the game engine will position the objects"
                        " for you. Do not use width and height if your object contains"
                        " text because it might bleed. Note that we use a dark theme. "
                        "Only output the HTML.",
                    },
                    {
                        "role": "user",
                        "content": "Render this object now: "
                        + json.dumps(object.dict()),
                    },
                ],
            )
            .choices[0]
            .message.content
        )
        result = fix_model_output(result, start="<", end=">")
        return RenderObjectResponse(html=result)
    except Exception as e:
        return render_object(request)


class ObjectInteraction(BaseModel):
    name: str
    display_name: str
    arguments: list[str] | None


class ObtainObjectInteractionsRequest(BaseModel):
    world: World
    object: WorldObject


class ObtainObjectInteractionsResponse(BaseModel):
    interactions: list[ObjectInteraction]


@app.post("/api/interact")
def obtain_object_interactions(
    request: ObtainObjectInteractionsRequest,
) -> ObtainObjectInteractionsResponse:
    try:
        world, object = request.world, request.object
        result = (
            openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are GameMasterAI. Your purpose is to generate"
                        " interactions between the player and objects in the world. "
                        "These interactions"
                        " must be simple but entertaining and must be accurrate to the"
                        " expectations of the player. The interactions must be"
                        " represented as a JSON list where each element is an object"
                        " with a name, a display_name, and arguments. The name is a unique"
                        " identifier for the interaction and the display_name is"
                        " what the player sees. Interactions also have arguments, "
                        " which are a list of questions that the player must answer to"
                        " complete the interaction."
                        "Here is an example interaction:"
                        '{"name": "eat", "display_name": "Eat", "arguments": '
                        '["What do you want to eat?"]}',
                    },
                    {
                        "role": "user",
                        "content": "World context: " + json.dumps(world.dict()),
                    },
                    {
                        "role": "user",
                        "content": "Return JSON interactions for object: "
                        + json.dumps(object.dict()),
                    },
                ],
            )
            .choices[0]
            .message.content
        )
        print(result)
        result = fix_model_output(result, start="[", end="]")

        # Turn the result into a ObtainObjectInteractionsResponse object
        interactions_dict = json.loads(result)
        if isinstance(interactions_dict, list):
            interactions_dict = {"interactions": interactions_dict}

        # Add "custom" interaction which is always available and allows the player
        # to type in a custom command
        interactions_dict["interactions"].append(
            {
                "name": "custom",
                "display_name": "Custom",
                "arguments": ["What do you want to do?"],
            }
        )

        interactions = ObtainObjectInteractionsResponse.parse_obj(interactions_dict)

        return interactions
    except Exception as e:
        return obtain_object_interactions(request)


class DoInteractRequest(BaseModel):
    world: World
    object: WorldObject
    interaction: ObjectInteraction


class DeleteObject(BaseModel):
    name: str


CreateObject = WorldObject

OverwriteMetadata = WorldObject


class DisplayMessage(BaseModel):
    message: str


class DoInteractResponse(BaseModel):
    delete_objects: list[DeleteObject] | None
    create_objects: list[CreateObject] | None
    overwrite_metadata: list[OverwriteMetadata] | None
    display_messages: list[DisplayMessage] | None


@app.post("/api/do_interaction")
def do_interact(request: DoInteractRequest) -> DoInteractResponse:
    try:
        world, object, interaction = request.world, request.object, request.interaction
        result = (
            openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "user",
                        "content": "World context: " + json.dumps(world.dict()),
                    },
                    {
                        "role": "system",
                        "content": "You are GameEngineAI. Your purpose is to execute"
                        " interactions between the player and objects in the world. "
                        "The world, object, and interaction are provided as JSON."
                        "You must return an object of effects that the interaction"
                        " had on the world. You can use the game_state object"
                        " metadata to set global variables that track the game"
                        " progress. "
                        "Only output the JSON. You can set metadata values to None"
                        " to delete them."
                        "Here is an example result that uses all"
                        " possible effects: \n"
                        + json.dumps(
                            {
                                "delete_objects": [
                                    {"name": "stick"},
                                    {"name": "rock"},
                                ],
                                "create_objects": [
                                    {
                                        "name": "axe",
                                        "metadata": {"color": "brown"},
                                    },
                                ],
                                "overwrite_metadata": [
                                    {
                                        "name": "player",
                                        "metadata": {"has_crafted": True},
                                    },
                                ],
                                "display_messages": [
                                    {"message": "Congrats!"},
                                ],
                            }
                        )
                        + "\nYou should prioritize creating and deleting objects "
                        "as this is more fun for the player. You should also challenge"
                        " the player by having certain interactions fail. For example,"
                        " if the player tries to eat a rock, you should show a message"
                        " that says 'You can't eat a rock!'. Some interactions should"
                        " also fail randomly, to represent a sense of difficulty."
                        " for example a cauldron might explode even if the player"
                        " correctly follows the recipe for a potion."
                        "You must not abuse display_messages by using it to display"
                        "things that didn't happen. For example, you can't say 'The"
                        "monster died!' if you don't also use delete_objects to delete"
                        "the monster. You must add new metadata and new objects"
                        " as the player discovers new things. For example, if the player"
                        " asks for the name of an NPC, you should add a new metadata"
                        " field to the NPC object that stores the name. This is "
                        "important, as otherwise you won't be able to remember"
                        " the name of the NPC later. You must also make sure to clean"
                        " up objects that are no longer needed. For example, if this"
                        " is a game about fixing cars and a car has already been fixed,"
                        " you should delete the broken car object.",
                    },
                    {
                        "role": "user",
                        "content": "Object context: " + json.dumps(object.dict()),
                    },
                    {
                        "role": "user",
                        "content": "Please return JSON effects for this interaction: "
                        + json.dumps(interaction.dict()),
                    },
                ],
            )
            .choices[0]
            .message.content
        )
        result = fix_model_output(result)

        # Turn the result into a DoInteractResponse object
        effects_dict = json.loads(result)
        return DoInteractResponse.parse_obj(effects_dict)
    except Exception as e:
        return do_interact(request)


class GameTickRequest(BaseModel):
    world: World


@app.post("/api/game_tick")
def do_interact(request: GameTickRequest) -> DoInteractResponse:
    try:
        world = request.world
        result = (
            openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "user",
                        "content": "World context: " + json.dumps(world.dict()),
                    },
                    {
                        "role": "system",
                        "content": "You are GameEngineAI. Your purpose is to compute"
                        " a game world tick."
                        "The world is provided as JSON."
                        "You must return a JSON object of effects that the tick"
                        " had on the world. You can use the game_state object"
                        " metadata to update global variables that track the game"
                        " progress. "
                        "Only output the JSON. You can set metadata values to None"
                        " to delete them."
                        "Here is an example result that uses all"
                        " possible effects: \n"
                        + json.dumps(
                            {
                                "delete_objects": [
                                    {"name": "seed"},
                                ],
                                "create_objects": [
                                    {
                                        "name": "plant",
                                        "metadata": {"growth": "1"},
                                    },
                                ],
                                "overwrite_metadata": [
                                    {
                                        "name": "calendar",
                                        "metadata": {"month": "february"},
                                    },
                                ],
                                "display_messages": [
                                    {"message": "Your plant grew!"},
                                ],
                            }
                        )
                        + "\nDuring the game tick, the world gets updated without"
                        " any player input. You should update the world to reflect"
                        " the change of time. For example, you can make plants grow"
                        ", or make the player hungry, or make enemies attack the"
                        "player, make loyalties change, etc. You should also"
                        " challenge the player by having new challenges and enemies"
                        " appear. For example, you can show a new quest, or a new"
                        " enemy, or a new friendly NPC. Do not perform any actions"
                        " that require player input. For example, if there is a"
                        " tree that the player can cut down, you should not cut"
                        " down the tree during the game tick. Instead, you should"
                        " make the tree grow older or something like that."
                        "You must not abuse display_messages by using it to display"
                        "things that didn't happen. For example, you can't say 'The"
                        "monster attacks you!' if you don't also use overwrite_metadata "
                        "to change the player's health. You also can't say something"
                        " like 'Helena is on her room' if there is no metadata that"
                        "backs this up. You must also make sure to clean"
                        " up objects that are no longer needed. For example, if this"
                        " is a game about fixing cars and a car has already been fixed,"
                        " you should delete the broken car object.",
                    },
                    {
                        "role": "user",
                        "content": "Please return JSON effects for this game tick now:",
                    },
                ],
            )
            .choices[0]
            .message.content
        )
        result = fix_model_output(result)

        # Turn the result into a DoInteractResponse object
        effects_dict = json.loads(result)
        return DoInteractResponse.parse_obj(effects_dict)
    except Exception as e:
        return do_interact(request)
