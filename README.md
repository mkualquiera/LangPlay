# LangPlay: Language-Modeled Game Engine

This is an experiment where I tried to use a language model to perform the
tasks that would normally be done by a game engine. 

Fundamentally, a game engine is a program that takes the specification of a 
game, and runs it. The specification of a game is usually a set of rules,
assets, and so on. At runtime, the game engine uses the specification 
to maintain a game state and listen to user input, which in turn changes
the game state. The game engine then renders the game state to the screen 
or other devices. The goal of this experiment is to use a language model
to perform these tasks.

For building the specification of a game, we can use a prompt that translates
a natural language input into the initial game state. For example, the prompt
`"A game where you are a knight and you have to slay a dragon"` can be used
to generate the initial game state that has a knight and a dragon, etc. In 
this case we represent the game state as a JSON object, as models such as
GPT-3.5 and GPT-4 can easily work with them. This game state is composed
of objects with names and metadata that can be used to render the game state
and such. 

For the user input, we use a prompt that takes the game state and a specific
object, and generates a list of actions that can be performed on that object.
These actions can have parameters, such as the direction to move, or the
amount of damage to inflict. 

Then, we can use another prompt as a sort of "state transition function" that
takes the game state and the action, and generates the new game state. 
Technically it generates a delta, but we get the new state by applying the
delta to the old state. 

Finally, we can use a prompt that takes the game state and renders each object
into HTML elements that can be displayed by a browser. This gives some creative
freedom to the model, as it can choose to render the objects in ways that
match the metadata and are visually interesting.

All of this is implemented in `main.py`, and the frontend is in 
`/static/index.html`.

# Running 

Create a `.env` file with your `OPENAI_API_KEY` as a variable. 

Install the requirements with `pip install -r requirements.txt`. Then, run
`uvicorn main:app` to start the server. 

Finally, browse `http://127.0.0.1:8000/static/index.html` or whatever port is 
used by uvicorn in your case.

# Contributing

First of all I apologize for the javascript code, I hate javascript and I
really didn't want to use something like React for something as simple as this.

Feel free to improve anything and open a pull request (including stuff like a React
port, I'm just too lazy to do it myself).