Classification
Classification is a classic problem in NLP and finds many applications: spam detection, sentiment analysis, triaging of incoming requests, etc. We will use the example of a company that wants to sort support requests between those that require immediate attention (URGENT), those that can wait a little (STANDARD). You could easily extend the example by adding new labels.

This tutorial shows how one can implement multi-label classification using Outlines. We will use two functionalities of the library: generate.choice and generate.json.

As always, we start with initializing the model. Since we are GPU poor we will be using a quantized version of Mistal-7B-v0.1:


import outlines

model = outlines.models.transformers("TheBloke/Mistral-7B-OpenOrca-AWQ", device="cuda")
We will use the following prompt template:


@outlines.prompt
def customer_support(request):
    """You are an experienced customer success manager.

    Given a request from a client, you need to determine when the
    request is urgent using the label "URGENT" or when it can wait
    a little with the label "STANDARD".

    # Examples

    Request: "How are you?"
    Label: STANDARD

    Request: "I need this fixed immediately!"
    Label: URGENT

    # TASK

    Request: {{ request }}
    Label: """
Choosing between multiple choices
Outlines provides a shortcut to do multi-label classification, using the outlines.generate.choice function to initialize a generator. Outlines uses multinomial sampling by default, here we will use the greedy sampler to get the label with the highest probability:


from outlines.samplers import greedy

generator = outlines.generate.choice(model, ["URGENT", "STANDARD"], sampler=greedy)
Outlines supports batched requests, so we will pass two requests to the model:

requests = [
    "My hair is one fire! Please help me!!!",
    "Just wanted to say hi"
]

prompts = [customer_support(request) for request in requests]
We can now asks the model to classify the requests:


labels = generator(prompts)
print(labels)
# ['URGENT', 'STANDARD']
Now, you might be in a hurry and don't want to wait until the model finishes completion. After all, you only need to see the first letter of the response to know whether the request is urgent or standard. You can instead stream the response:


tokens = generator.stream(prompts)
labels = ["URGENT" if "U" in token else "STANDARD" for token in next(tokens)]
print(labels)
# ['URGENT', 'STANDARD']
Using JSON-structured generation
Another (convoluted) way to do multi-label classification is to JSON-structured generation in Outlines. We first need to define our Pydantic schema that contains the labels:


from enum import Enum
from pydantic import BaseModel


class Label(str, Enum):
    urgent = "URGENT"
    standard = "STANDARD"


class Classification(BaseModel):
    label: Label
and we can use generate.json by passing this Pydantic model we just defined, and call the generator:


generator = outlines.generate.json(model, Classification, sampler=greedy)
labels = generator(prompts)
print(labels)
# [Classification(label=<Label.urgent: 'URGENT'>), Classification(label=<Label.standard: 'STANDARD



Named entity extraction
Named Entity Extraction is a fundamental problem in NLP. It involves identifying and categorizing named entities within a document: people, organization, dates, places, etc. It is usually the first step in a more complex NLP worklow. Here we will use the example of a pizza restaurant that receives orders via their website and need to identify the number and types of pizzas that are being ordered.

Getting LLMs to output the extracted entities in a structured format can be challenging. In this tutorial we will see how we can use Outlines' JSON-structured generation to extract entities from a document and return them in a valid JSON data structure 100% of the time.

As always, we start with initializing the model. We will be using a quantized version of Mistal-7B-v0.1 (we're GPU poor):


import outlines

model = outlines.models.transformers("TheBloke/Mistral-7B-OpenOrca-AWQ", device="cuda")
And we will be using the following prompt template:


@outlines.prompt
def take_order(order):
    """You are the owner of a pizza parlor. Customers \
    send you orders from which you need to extract:

    1. The pizza that is ordered
    2. The number of pizzas

    # EXAMPLE

    ORDER: I would like one Margherita pizza
    RESULT: {"pizza": "Margherita", "number": 1}

    # OUTPUT INSTRUCTIONS

    Answer in valid JSON. Here are the different objects relevant for the output:

    Order:
        pizza (str): name of the pizza
        number (int): number of pizzas

    Return a valid JSON of type "Order"

    # OUTPUT

    ORDER: {{ order }}
    RESULT: """
We now define our data model using Pydantic:


from enum import Enum
from pydantic import BaseModel

class Pizza(str, Enum):
    margherita = "Margherita"
    pepperonni = "Pepperoni"
    calzone = "Calzone"

class Order(BaseModel):
    pizza: Pizza
    number: int
We can now define our generator and call it on several incoming orders:


orders = [
    "Hi! I would like to order two pepperonni pizzas and would like them in 30mins.",
    "Is it possible to get 12 margheritas?"
]
prompts = [take_order(order) for order in orders]

generator = outlines.generate.json(model, Order)

results = generator(prompts)
print(results)
# [Order(pizza=<Pizza.pepperonni: 'Pepperoni'>, number=2),
#  Order(pizza=<Pizza.margherita: 'Margherita'>, number=12)]
There are several ways you could improve this example:

Clients may order several types of pizzas.
Clients may order drinks as well.
If the pizza place has a delivery service we need to extract the client's address and phone number
Clients may specify the time for which they want the pizza. We could then check against a queuing system and reply to them with the estimated delivery time.
How would you change the Pydantic model to account for these use cases?


Generate a synthetic dating profile from a description
In this example we will see how we can use Outlines to generate synthetic data for a dating application. This example was originally contributed by Vibhor Kumar.


from dataclasses import dataclass
from enum import Enum

import torch
import transformers
from pydantic import BaseModel, conlist, constr

import outlines
Defining the profile with Pydantic
Here a dating profile will consist in a biography, a job, a list of interests and two question-answer pairs. The questions are written in advance by the team, and the users are asked to provide an answer:


class QuestionChoice(str, Enum):
    A = "The key to my heart is"
    B = "The first item on my bucket list is"
    C = "Perks of dating me"
    D = "Message me if you also love"
    E = "People would describe me as"
    F = "I can beat you in a game of"

@dataclass
class QuestionAnswer:
    question: QuestionChoice
    answer: str
Users need to provide a short biography, with a minimum of 10 and a maximum of 300 characters. The application also limits job descriptions to 50 characters. In addition to the question-answer pairs, the user is required to provide a list of between 1 and 5 interests:


class DatingProfile(BaseModel):
    bio: constr(str, min_length=10, max_length=300)
    job: constr(str, max_lengt=50)
    interests: conlist(str, min_length=1, max_length=5)  # type: ignore
    qna1: QuestionAnswer
    qna2: QuestionAnswer
Prompt template and examples
We will ask the model to generate profiles from a high-level description:


@dataclass
class Example:
    description: str
    profile: DatingProfile
We will use Outlines' prompt templating abilities to generate the prompt for us. This help clearly separate the general prompting logic from what is specific to an example.


@outlines.prompt
def dating_profile_prompt(description: str, examples: list[Example]):
    """
    You are a world-renowned matchmaker who understands the modern dating
    market. Your job is to generate dating app profiles for male clients
    interested in women based on a provided description. The profiles should be
    authentic, show off their strengths, and maximize their likelihood of
    getting matches on dating apps.  Here are some examples of past clients that
    you have successfully created profiles for:

    {% for example in examples %}
    Description:
    {{ example.description }}
    Profile:
    {{ example.profile }}
    {% endfor %}

    Here is the new client who you need to create a profile for:
    Description: {{ description }}
    Profile:
    """
We will provide the model with several few-shot examples:


samples: list[Example] = [
    Example(
        description="I'm an author and former professional soccer player living in Seattle who publishes popular fiction books. A typical day for me starts by hanging out with my cat, drinking a coffee, and reading as much as I can in a few hours. Then, I'll prepare a quick smoothie before starting to write for a few hours, take a break with soccer or running a few miles, and finally meet friends for dinner at a new, hip restaurant in the evening. Sometimes we go axe-throwing afterwards, or play poker, or watch a comedy show, or visit a dive bar. On my vacations, I travel extensively to countries South America, Europe, and Asia, with the goal of visiting them all!",
        profile=DatingProfile(
            bio="Adventurer, dreamer, author, and soccer enthusiast. Life’s too short to waste time so I make the most of each day by exploring new places and playing with my friends on the pitch. What’s your favorite way to get out and have fun?",
            job="Famous Soccer Player -> Famous Author",
            interests=["Soccer", "Travel", "Friends", "Books", "Fluffy Animals"],
            qna1=QuestionAnswer(
                question=QuestionChoice.B, answer="swim in all seven oceans!"
            ),
            qna2=QuestionAnswer(
                question=QuestionChoice.E,
                answer="fun-loving, adventurous, and a little bit crazy",
            ),
        ),
    ),
    Example(
        description="I run my company and build houses for a living. I'm a big fan of the outdoors and love to go hiking, camping, and fishing. I don't like video games, but do like to watch movies. My love language is home-cooked food, and I'm looking for someone who isn't afraid to get their hands dirty.",
        profile=DatingProfile(
            bio="If you're looking for a Montana man who loves to get outdoors and hunt, and who's in-tune with his masculinity then I'm your guy!",
            job="House Construction Manager / Entrepreneur",
            interests=["Hunting", "Hiking", "The outdoors", "Home-cooked food"],
            qna1=QuestionAnswer(question=QuestionChoice.A, answer="food made at home"),
            qna2=QuestionAnswer(
                question=QuestionChoice.C,
                answer="having a man in your life who can fix anything",
            ),
        ),
    ),
    Example(
        description="I run my own Youtube channel with 10M subscribers. I love working with kids, and my audience skews pretty young too. In my free time, I play Fortnite and Roblox. I'm looking for someone who is also a gamer and likes to have fun. I'm learning Japanese in my free time as well as how to cook.",
        profile=DatingProfile(
            bio="Easy on the eyes (find me on Youtube!) and great with kids. What more do you need?",
            job="Youtuber 10M+ subscribers",
            interests=["Kids", "Gaming", "Japanese"],
            qna1=QuestionAnswer(question=QuestionChoice.D, answer="anime and gaming!"),
            qna2=QuestionAnswer(question=QuestionChoice.F, answer="Fortnite, gg ez"),
        ),
    ),
]
Load the model
We will use Mosaic's MPT-7B model (requires 13GB of GPU memory) which can fit on a single GPU with a reasonable context window. We initialize it with Outlines:


config = transformers.AutoConfig.from_pretrained(
    "mosaicml/mpt-7b-8k-instruct", trust_remote_code=True
)
config.init_device = "meta"
model = outlines.models.transformers(
    model_name="mosaicml/mpt-7b-8k-instruct",
    device="cuda",
    model_kwargs={
        "config": config,
        "trust_remote_code": True,
        "torch_dtype": torch.bfloat16,
        "device_map": {"": 0},
    },
)
JSON-structured generation of profiles
We will now generate a dating profile from a textual description of oneself:


new_description = """I'm a laid-back lawyer who spends a lot of his free-time
gaming. I work in a corporate office, but ended up here after the start-up  I
cofounded got acquired, so still play ping pong with my cool coworkers every
day.  I have a bar at home where I make cocktails, which is great for
entertaining  friends. I secretly like to wear suits and get a new one tailored
every few  months. I also like weddings because I get to wear those suits, and
it's  a good excuse for a date. I watch the latest series because I'm paying,
with my hard-earned money, for every streaming service."""

prompt = dating_profile_prompt(new_description, samples)
profile = outlines.generate.json(model, DatingProfile)(prompt)
parsed_profile = DatingProfile.model_validate_json(profile)
Results
Here are a couple of results:


{
    "bio": """I'm an ambitious lawyer with a casual and fashionable style. I love
    games and sports, but my true passion is preparing refreshing cocktails at
    home and dressing to the nines at weddings. I'm currently looking for a woman
    to show a good time to and get a kiss on the opulent suit I just had made.
    Send resume to this inbox.""",
    "job": "Lawyer",
    "interests":
    [
        "Stylish guys",
        "Gaming",
        "Ping pong",
        "Cocktails",
        "Weddings"
    ],
    "qna1":
    {
        "question": "The first item on my bucket list is",
        "answer": "be married and have a family."
    },
    "qna2":
    {
        "question": "People would describe me as",
        "answer": "charming, stylish, and funny."
    }
}

{
    "bio": """I’m a sexy lawyer with time on my hands. I love to game and
    play ping pong, but the real reason you should swipe to the right
    is because I look great in a suit. Who doesn’t love a man in a
    suit? Just saying. Send me a message if you think it’s time to take
    your dating life to the next level.""",
    "job": "Lawyer",
    "interests":
    [
        "Gaming",
        "Ping Pong",
        "Tailored Suits",
        "Weddings",
        "Streaming Services"
    ],
    "qna1":
    {
        "question": "The first item on my bucket list is",
        "answer": "simulate space but stay alive for as long as possible"
    },
    "qna2":
    {
        "question": "People would describe me as",
        "answer": "easy-going, a little nerdy but with a mature essence"
    }
}


Summarize documents using Chain of Density prompting
A good summary should be informative, concise and clear. While large language models are generally good at summarizing documents, their summaries tend to be long and contain redundant information; their information density tends to be on the lower end. This is where chain of Density, a new prompting technique, comes in. In this example we will show how one can implement chain of density with a few lines of code using Outlines, leveraging both Outline's prompt templating and its structured generation capabilities.

The article we will try to summarize is the first three paragraphs of the Alan Turing page on Wikipedia:


article = """
Alan Mathison Turing OBE FRS (/ˈtjʊərɪŋ/; 23 June 1912 – 7 June 1954) was an English mathematician, computer scientist, logician, cryptanalyst, philosopher and theoretical biologist.[5] Turing was highly influential in the development of theoretical computer science, providing a formalisation of the concepts of algorithm and computation with the Turing machine, which can be considered a model of a general-purpose computer.[6][7][8] He is widely considered to be the father of theoretical computer science and artificial intelligence.[9]

Born in Maida Vale, London, Turing was raised in southern England. He graduated at King's College, Cambridge, with a degree in mathematics. Whilst he was a fellow at Cambridge, he published a proof demonstrating that some purely mathematical yes–no questions can never be answered by computation. He defined a Turing machine and proved that the halting problem for Turing machines is undecidable. In 1938, he obtained his PhD from the Department of Mathematics at Princeton University. During the Second World War, Turing worked for the Government Code and Cypher School at Bletchley Park, Britain's codebreaking centre that produced Ultra intelligence. For a time he led Hut 8, the section that was responsible for German naval cryptanalysis. Here, he devised a number of techniques for speeding the breaking of German ciphers, including improvements to the pre-war Polish bomba method, an electromechanical machine that could find settings for the Enigma machine. Turing played a crucial role in cracking intercepted coded messages that enabled the Allies to defeat the Axis powers in many crucial engagements, including the Battle of the Atlantic.[10][11]

After the war, Turing worked at the National Physical Laboratory, where he designed the Automatic Computing Engine, one of the first designs for a stored-program computer. In 1948, Turing joined Max Newman's Computing Machine Laboratory at the Victoria University of Manchester, where he helped develop the Manchester computers[12] and became interested in mathematical biology. He wrote a paper on the chemical basis of morphogenesis[1] and predicted oscillating chemical reactions such as the Belousov–Zhabotinsky reaction, first observed in the 1960s. Despite these accomplishments, Turing was never fully recognised in Britain during his lifetime because much of his work was covered by the Official Secrets Act.[13]
"""
How Chain Of Density works
Chain Of Density starts with asking the model to generate a first long and non-specific summary. Then it asks the model to generate 4 extra summaries by proceeding in the following way:

Identify 1-3 entities missing in the previous summary;
Add all entities marked as missing in the previous step, while not dropping entities;
Make the summary more concise;
The prompt also asks the model to return a list of JSON objects that contain the missing entities and the new summary. This is where structured generation will come in handy :) The paper provides the prompt and an example:

Figure 2 in the paper

We can now implement the prompt provided in the paper:


import outlines

@outlines.prompt
def chain_of_density(article):
    """Article: {{ article }}

    You will generate increasingly concise, entity-dense summaries of the above Article.

    Repeat the following 2 steps 5 times.

    Step 1. Identify 1-3 informative Entities ("; " delimited) from the Article which are missing from the previously generated summary.
    Step 2. Write a new, denser summary of identical length which covers every entity and detail from the previous summary plus the Missing Entities.

    A Missing Entity is:
    - Relevant: to the main story.
    - Specific: descriptive yet concise (5 words or fewer).
    - Novel: not in the previous summary.
    - Faithful: present in the Article.
    - Anywhere: located anywhere in the Article.

    Guidelines:
    - The first summary should be long (4-5 sentences, ~80 words) yet highly non-specific, containing little information beyond the entities marked as missing. Use overly verbose language and fillers (e.g., "this article discusses") to reach ~80 words.
    - Make every word count: rewrite the previous summary to improve flow and make space for additional entities.
    - Make space with fusion, compression, and removal of uninformative phrases like "the article discusses".
    - The summaries should become highly dense and concise yet self-contained, e.g., easily understood without the Article.
    - Missing entities can appear anywhere in the new summary.
    - Never drop entities from the previous summary. If space cannot be made, add fewer new entities.

    Remember, use the exact same number of words for each summary.

    Answer in JSON. The JSON should be a a dictionary with key "summaries" that contains a list (length 5) of dictionaries whose keys are "Missing_Entities" and "Denser_Summary".
    """
Note
Outlines implementation
We will use Outline's JSON-structured generation to ensure that the model's output is consistent with the format specified in the prompt. We start with defining the JSON objects that the model is asked to return using Pydantic. One JSON object that contains a list of Summary objects that contain the missing entities and new summary:


from pydantic import BaseModel, conlist

class Summary(BaseModel):
    missing_entities: str
    denser_summary: str

class Summaries(BaseModel):
    summaries: conlist(Summary, max_length=5, min_length=5)
We now generate the prompt by passing the article we want to summarize to the template. We load a quantized version of Mistral-7B using the AutoAWQ library, and then use JSON-structured generation to generate the summaries:


model = outlines.models.transformers("TheBloke/Mistral-7B-OpenOrca-AWQ")

prompt = chain_of_density(article)
result = outlines.generate.json(model, Summaries)(prompt)
We can now check the results:


print(result.model_dump())
# {'summaries': [
#     {
#       'missing_entities': 'English mathematician, cryptanalyst, philosopher',
#       'denser_summary': 'Alan Mathison Turing was an English mathematician, cryptanalyst, philosopher.'
#     },
#     {
#       'missing_entities': '',
#       'denser_summary': "Alan Mathison Turing was an English mathematician who was a crucial figure in WW2's Bletchley Park codebreaking centre and designed one of the first computers."
#     },
#     {
#       'missing_entities': 'cryptanalyst, studied, biology, father',
#       'denser_summary': 'Alan Mathison Turing was an English cryptanalyst, studied theoretical computer science, and contributed to mathematical biology.'
#     },
#     {
#       'missing_entities': 'biology, morphogenesis, chemical',
#       'denser_summary': 'Alan Mathison Turing was an English cryptanalyst, studied theoretical computer science, and predicted chemical reactions in morphogenesis.
#     '},
#     {
#       'missing_entities': '',
#       'denser_summary': 'Alan Mathison Turing was an English cryptanalyst, developed computer science, and made strides in mathematical biology research.'
#       }
# ]}
Not bad, considering we used a smallish model to generate the summary! Chain of Density seems to be a very effective prompting technique to generate dense summaries, even with small quantized models. Its implementation in Outlines is also very short.

Note that this is the first article I tried and it worked out of the box. Try it out on other articles, and please share the results on Twitter, or by opening a new discussion on the Outlines repository!



Large language models playing chess
In this example we will make a Phi-2 model play chess against itself. On its own the model easily generates invalid moves, so we will give it a little help. At each step we will generate a regex that only matches valid move, and use it to help the model only generating valid moves.

The chessboard
The game will be played on a standard checkboard. We will use the chess library to track the opponents' moves, and check that the moves are valid.


%pip install outlines -q
%pip install chess -q
%pip install transformers accelerate einops -q

import chess

board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
The opponents
Phi-2 will be playing against itself:


from outlines import models

model = models.transformers("microsoft/phi-2")
A little help for the language model
To make sure Phi-2 generates valid chess moves we will use Outline's regex-structured generation. We define a function that takes the current state of the board and returns a regex that matches all possible legal moves:


import re

def legal_moves_regex(board):
    """Build a regex that only matches valid moves."""
    legal_moves = list(board.legal_moves)
    legal_modes_str = [board.san(move) for move in legal_moves]
    legal_modes_str = [re.sub(r"[+#]", "", move) for move in legal_modes_str]
    regex_pattern = "|".join(re.escape(move) for move in legal_modes_str)
    regex_pattern = f"{regex_pattern}"
    return regex_pattern
Prompting the language model
The prompt corresponds to the current state of the board, so we start with:


prompt = "Let's play Chess. Moves: "
We update the prompt at each step so it reflects the state of the board after the previous move.

Let's play

from outlines import generate

board_state = " "
turn_number = 0
while not board.is_game_over():
    regex_pattern = legal_moves_regex(board)
    structured = generate.regex(model, regex_pattern)(prompt + board_state)
    move = board.parse_san(structured)

    if turn_number % 2 == 0 :  # It's White's turn
        board_state += board.san(move) + " "
    else:
        board_state += board.san(move) + " " + str(turn_number) + "."

    turn_number += 1

    board.push(move)

    print(board_state)
Interestingly enough, Phi-2 hates capturing.


 e4 e5 1.Nf3 Ne7 3.b4 Nf5 5.Nc3 Ne7 7.Bb5 a6 9.Na4 b6 11.c3 Nec6 13.c4 a5 15.d4 Qg5 17.Nd2 Bb7 19.dxe5
This example was originally authored by @903124S in this gist.



Reference
Structured generation
While LLM capabilities are increasingly impressive, we can make their output more reliable by steering the generation. Outlines thus offers mechanisms to specify high level constraints on text completions by generative language models.

Stopping sequence By default, language models stop generating tokens after and token was generated, or after a set maximum number of tokens. Their output can be verbose, and for practical purposes it is often necessary to stop the generation after a given sequence has been found instead. You can use the stop_at keyword argument when calling the model with a prompt:


import outlines.models as models

complete = models.openai("gpt-3.5-turbo")
expert = complete("Name an expert in quantum gravity.", stop_at=["\n", "."])


Text generation
Outlines provides a unified interface to generate text with many language models, API-based and local. The same pattern is used throughout the library:

Instantiate a generator by calling outlines.generate.text with the model to be used.
Call the generator with the prompt and (optionally) some generation parameters.

from outlines import models, generate

model = models.openai("gpt-4")
generator = generate.text(model)
answer = generator("What is 2+2?")

model = models.transformers("mistralai/Mistral-7B-v0.1")
generator = generate.text(model)
answer = generator("What is 2+2?")
By default Outlines uses the multinomial sampler with temperature=1. See this section to learn how to use different samplers.

Streaming
Outlines allows you to stream the model's response by calling the .stream method of the generator with the prompt:


from outlines import models, generate

model = models.transformers("mistralai/Mistral-7B-v0.1")
generator = generate.text(model)

tokens = generator.stream("What is 2+2?")
for token in tokens:
    print(token)
Parameters
Limit the number of tokens generated
To limit the number of tokens generated you can pass the max_tokens positional argument to the generator:


from outlines import models, generate

model = models.transformers("mistralai/Mistral-7B-v0.1")
generator = generate.text(model)

answer = generator("What is 2+2?", 5)
answer = generator("What is 2+2?", max_tokens=5)
Stop after a given string is generated
You can also ask the model to stop generating text after a given string has been generated, for instance a period or a line break. You can pass a string or a line of string for the stop_at argument:


from outlines import models, generate

model = models.transformers("mistralai/Mistral-7B-v0.1")
generator = generate.text(model)

answer = generator("What is 2+2?", stop_at=".")
answer = generator("What is 2+2?", stop_at=[".", "\n"])
The stopping string will be included in the response.

Seed the generation
It can be useful to seed the generation in order to get reproducible results:


import torch
from outlines import models, generate

model = models.transformers("mistralai/Mistral-7B-v0.1")

rng = torch.Generator(device="cuda")
rng.manual_seed(789001)

answer = generator("What is 2+2?", rng=rng)


Samplers
Outlines offers different sequence sampling algorithms, and we will integrate more in the future. You can read this blog post for an overview of the different sampling algorithm.

Multinomial sampling
Outlines defaults to the multinomial sampler without top-p or top-k sampling, and temperature equal to 1. Not specifying a sampler is equivalent to:


from outlines import models, generate, samplers


model = models.transformers("mistralai/Mistral-7B-0.1")
sampler = samplers.multinomial()

generator = generate.text(model, sampler)
answer = generator("What is 2+2?")

print(answer)
# 4
You can ask the generator to take multiple samples by passing the number of samples when initializing the sampler:


from outlines import models, generate, samplers


model = models.transformers("mistralai/Mistral-7B-0.1")
sampler = samplers.multinomial(3)

generator = generate.text(model, sampler)
answer = generator("What is 2+2?")

print(answer)
# [4, 4, 4]
If you ask multiple samples for a batch of prompt the returned array will be of shape (num_samples, num_batches):


from outlines import models, generate, samplers


model = models.transformers("mistralai/Mistral-7B-0.1")
sampler = samplers.multinomial(3)

generator = generate.text(model, sampler)
answer = generator(["What is 2+2?", "What is 3+3?"])

print(answer)
# [[4, 4, 4], [6, 6, 6]]
Top-k sampling
You can ask Outlines to only consider the top-k logits at each step by specifying the value of the top-k keyword argument when initializing the sampler.


sampler = samplers.multinomial(3, top_k=10)
Top-p sampling
You can ask Outlines to only consider the highest probability tokens such that their cumulative probability is greater than a threshold p. Specify the top_p keyword argument when initializing the sampler:


sampler = samplers.multinomial(3, top_p=0.95)
Greedy sampler
You can also use the greedy sampler. For this you need to initialize the generator with the sampler:


from outlines import models, generate, samplers


model = models.transformers("mistralai/Mistral-7B-0.1")
sampler = samplers.greedy()

generator = generate.text(model, sampler)
answer = generator("What is 2+2?")

print(answer)
# 4
You cannot ask for multiple samples with the greedy sampler since it does not clear what the result should be.

Beam Search
Outlines also comes with the Beam Search sampling algorithm:


from outlines import models, generate, samplers


model = models.transformers("mistralai/Mistral-7B-Instruct-v0.2")
sampler = samplers.beam_search(beams=5)

generator = generate.text(model, sampler)
answer = generator("What is 2+2?")

print(answer)
# 4
Compatibility

Only models from the transformers and exllamav2 libraries are compatible with Beam Search.

Multiple choices
Oultines allows you to make sure the generated text is chosen between different options:


from outlines import models, generate

model = models.transformers("mistralai/Mistral-7B-v0.1")
generator = generate.choice(model, ["skirt", "dress", "pen", "jacket"])
answer = generator("Pick the odd word out: skirt, dress, pen, jacket")
Performance

generation.choice computes an index that helps Outlines guide generation. This can take some time, but only needs to be done once. If you want to generate from the same list of choices several times make sure that you only call generate.choice once.

Regular expressions
Outlines can guarantee that the text generated by the LLM will be valid to a regular expression:


from outlines import models, generate

model = models.transformers("mistralai/Mistral-7B-Instruct-v0.2")

generator = generate.regex(
    model,
    r"((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)",
)

prompt = "What is the IP address of the Google DNS servers? "
answer = generator(prompt, max_tokens=30)

print(answer)
# What is the IP address of the Google DNS servers?
# 2.2.6.1
If you find yourself using generate.regex to restrict the answers' type you can take a look at type-structured generation instead.

Performance

generate.regex computes an index that helps Outlines guide generation. This can take some time, but only needs to be done once. If you want to generate several times using the same regular expression make sure that you only call generate.regex once.


Type constraints
We can ask completions to be restricted to valid python types:


from outlines import models, generate

model = models.transformers("mistralai/Mistral-7B-v0.1")
generator = generate.format(model, int)
answer = generator("When I was 6 my sister was half my age. Now I’m 70 how old is my sister?")
print(answer)
# 67
The following types are currently available:

int
float
bool
datetime.date
datetime.time
datetime.datetime


JSON structured generation
Outlines can make any open source model return a JSON object that follows a structure that is specified by the user. This is useful whenever we want the output of the model to be processed by code downstream: code does not understand natural language but rather the structured language it has been programmed to understand.

There are mostly two reasons why someone would want to get an output formatted as JSON from a LLM:

Parse the answer (e.g. with Pydantic), store it somewhere, return it to a user, etc.
Call a function with the result
Outlines has you covered in both cases! Indeed, to define the structure of the JSON you want the model to follow you can either provide a Pydantic model, or a function. No need to duplicate code!

Using Pydantic
Outlines can infer the structure of the output from a Pydantic model. The result is an instance of the model that contains the values returned by the LLM:


from pydantic import BaseModel

from outlines import models, generate


class User(BaseModel):
    name: str
    last_name: str
    id: int


model = models.transformers("mistralai/Mistral-7B-v0.1")
generator = generate.json(model, User)
result = generator(
    "Create a user profile with the fields name, last_name and id"
)
print(result)
# User(name="John", last_name="Doe", id=11)
JSON and whitespaces

By default Outlines lets model choose the number of linebreaks and white spaces used to structure the JSON. Small models tend to struggle with this, in which case we recommend to set the value of the parameter whitespace_pattern to the empty string:


generator = generate.json(model, User, whitespace_pattern="")
Performance

generation.json computes an index that helps Outlines guide generation. This can take some time, but only needs to be done once. If you want to generate several times with the same schema make sure that you only call generate.json once.

Using a JSON Schema
Instead of a Pydantic model you can pass a string that represents a JSON Schema specification to generate.json:


from pydantic import BaseModel

from outlines import models
from outlines import text

model = models.transformers("mistralai/Mistral-7B-v0.1")

schema = """
{
  "title": "User",
  "type": "object",
  "properties": {
    "name": {"type": "string"},
    "last_name": {"type": "string"},
    "id": {"type": "integer"}
  }
}
"""

generator = generate.json(model, schema)
result = generator(
    "Create a user profile with the fields name, last_name and id"
)
print(result)
# User(name="John", last_name="Doe", id=11)
From a function's signature
Outlines can infer the structure of the output from the signature of a function. The result is a dictionary, and can be passed directly to the function using the usual dictionary expansion syntax **:


from outlines import models
from outlines import text

def add(a: int, b: int):
    return a + b

model = models.transformers("mistralai/Mistral-7B-v0.1")
generator = text.generate.json(model, add)
result = generator("Return two integers named a and b respectively. a is odd and b even.")

print(add(**result))
# 3
A great advantage of passing functions directly to specify the structure is that the structure of the LLM will change with the function's definition. No need to change the code at several places!


JSON mode
Outlines can guarantee that the LLM will generate valid JSON, using Grammar-structured generation:


from outlines import models, generate

json_grammar = outlines.grammars.json

model = models.transformers("mistralai/Mistral-7b-v0.1")
generator = generate.cfg(model, json_grammar)
sequence = generator("Generate valid JSON")
JSON that follows a schema

If you want to guarantee that the generated JSON follows a given schema, consult this section instead.


Grammar-structured generation
You can pass any context-free grammar in the EBNF format and Outlines will generate an output that is valid to this grammar:


from outlines import models, generate

arithmetic_grammar = """
    ?start: expression

    ?expression: term (("+" | "-") term)*

    ?term: factor (("*" | "/") factor)*

    ?factor: NUMBER
           | "-" factor
           | "(" expression ")"

    %import common.NUMBER
"""

model = models.transformers("WizardLM/WizardMath-7B-V1.1")
generator = generate.cfg(model, arithmetic_grammar)
sequence = generator(
  "Alice had 4 apples and Bob ate 2. "
  + "Write an expression for Alice's apples:"
)

print(sequence)
# (8-2)
Performance

The implementation of grammar-structured generation in Outlines is very naive. This does not reflect the performance of .txt's product, where we made grammar-structured generation as fast as regex-structured generation.

Ready-to-use grammars
Outlines contains a (small) library of grammars that can be imported and use directly. We can rewrite the previous example as:


from outlines import models, generate

arithmetic_grammar = outlines.grammars.arithmetic

model = models.transformers("WizardLM/WizardMath-7B-V1.1")
generator = generate.cfg(model, arithmetic_grammar)
sequence = generator(
  "Alice had 4 apples and Bob ate 2. "
  + "Write an expression for Alice's apples:"
)

print(sequence)
# (8-2)
The following grammars are currently available:

Arithmetic grammar via outlines.grammars.arithmetic
JSON grammar via outlines.grammars.json
If you would like more grammars to be added to the repository, please open an issue or a pull request.

Custom FSM Operations
Outlines is fast because it compiles regular expressions into an index ahead of inference. To do so we use the equivalence between regular expressions and Finite State Machines (FSMs), and the library interegular to perform the translation.

Alternatively, one can pass a FSM built using integular directly to structure the generation.

Example
Using the difference operation
In the following example we build a fsm which recognizes only the strings valid to the first regular expression but not the second. In particular, it will prevent the words "pink" and "elephant" from being generated:


import interegular
from outlines import models, generate


list_of_strings_pattern = """\["[^"\s]*"(?:,"[^"\s]*")*\]"""
pink_elephant_pattern = """.*(pink|elephant).*"""

list_of_strings_fsm = interegular.parse_pattern(list_of_strings_pattern).to_fsm()
pink_elephant_fsm = interegular.parse_pattern(pink_elephant_pattern).to_fsm()

difference_fsm = list_of_strings_fsm - pink_elephant_fsm

difference_fsm_fsm.accepts('["a","pink","elephant"]')
# False
difference_fsm_fsm.accepts('["a","blue","donkey"]')
# True


model = models.transformers("mistralai/Mistral-7B-Instruct-v0.2")
generator = generate.fsm(model, difference_fsm)
response = generator("Don't talk about pink elephants")
To see the other operations available, consult interegular's documentation.


Prompt templating
Outlines provides a powerful domain-specific language to write and manage prompts, via what we call prompt functions. Prompt functions are Python functions that contain a template for the prompt in their docstring, and their arguments correspond to the variables used in the prompt. When called, a prompt function returns the template rendered with the values of the arguments.

The aim of prompt functions is to solve several recurrent problems with prompting:

Building complex prompts quickly leads to messy code. This problem has already been solved in the web development community by using templating, so why not use it here?
Composing prompts is difficult. Why not just compose functions?
Separating prompts from code. Encapsulation in functions allows a clean separation between prompts and code. Moreover, like any function, prompt functions can be imported from other modules.
Outlines uses the Jinja templating engine to render prompts, which allows to easily compose complex prompts.

Prompt rendering

Prompt functions are opinionated when it comes to prompt rendering. These opinions are meant to avoid common prompting errors, but can have unintended consequences if you are doing something unusual. We advise to always print the prompt before using it. You can also read the reference section if you want to know more.

Your first prompt
The following snippet showcases a very simple prompt. The variables between curly brackets {{ }} are placeholders for the values of the arguments you will pass to the prompt function.


Code
Output

import outlines

@outlines.prompt
def greetings(name, question):
    """Hello, {{ name }}!
    {{ question }}
    """

prompt = greetings("user", "How are you?")
print(prompt)

If a variable is missing in the function's arguments, Jinja2 will throw an UndefinedError exception:


Code
Output

import outlines

@outlines.prompt
def greetings(name):
    """Hello, {{ surname }}!"""

prompt = greetings("user")

Importing prompt functions
Prompt functions are functions, and thus can be imported from other modules:


prompts.py
generate.py
Output

import outlines

@outlines.prompt
def greetings(name, question):
    """Hello, {{ name }}!
    {{ question }}
    """

Few-shot prompting
Few-shot prompting can lead to messy code. Prompt functions allow you to loop over lists or dictionaries from the template. In the following example we demonstrate how we can generate a prompt by passing a list of dictionaries with keys question and answer to the prompt function:


Code
Output

import outlines

@outlines.prompt
def few_shots(instructions, examples, question):
    """{{ instructions }}

    Examples
    --------

    {% for example in examples %}
    Q: {{ example.question }}
    A: {{ example.answer }}

    {% endfor %}
    Question
    --------

    Q: {{ question }}
    A:
    """

instructions = "Please answer the following question following the examples"
examples = [
    {"question": "2+2=?", "answer":4},
    {"question": "3+3=?", "answer":6}
]
question = "4+4 = ?"

prompt = few_shots(instructions, examples, question)
print(prompt)

Conditionals, filters, etc.
Jinja2 has many features beyond looping that are not described here: conditionals, filtering, formatting, etc. Please refer to the Jinja documentation for more information about the syntax of the templating language. The Jinja syntax is powerful, and we recommend you take some time to read their documentation if you are building complex prompts.

Tools
Several projects (e.g.Toolformer, ViperGPT, AutoGPT, etc.) have shown that we can "teach" language models to use external functions by describing what these functions do in the prompt. In these projects the same information is often repeated twice: the function implementation, name, docstring, or arguments are copy-pasted in the prompt. This is cumbersome and error prone; you can directly pull this information from within an Outlines prompt function:


Code
Output

import outlines

def my_tool(arg1: str, arg2: int):
    """Tool description.

    The rest of the docstring
    """
    pass

@outlines.prompt
def tool_prompt(question, tool):
    """{{ question }}

    COMMANDS
    1. {{ tool | name }}: {{ tool | description }}, args: {{ tool | args }}

    {{ tool | source }}
    """

prompt = tool_prompt("Can you do something?", my_tool)
print(prompt)

JSON response format
To build reliable chains with language models we often need to instruct them the format in which we would like them to return their response.

Without prompt templating, the information is repeated twice between creating the parsing function (e.g. a Pydantic model), and writing the desired schema in the prompt. This can lead to errors that are hard to debug.

Outlines allows you to directly pull the JSON schema of a pydantic model, or pretty print a dictionary from within an Outlines prompt function


Code
Output

from pydantic import BaseModel, Field

import outlines

class MyResponse(BaseModel):
    field1: int = Field(description="an int")
    field2: str

@outlines.prompt
def my_prompt(response_model):
    """{{ response_model | schema }}"""

my_prompt(MyResponse)
# {
#   "field1": "an int",
#   "field2": "<field2>"
# }

Formatting conventions
Prompt functions are opinionated when it comes to rendering, and these opinions are meant to avoid prompting mistakes and help with formatting.

Whitespaces
If you have experience working with strings between triple quotes you know that indenting has an influence on the string's formatting. Prompt functions adopt a few conventions so you don't have to think about indents when writing prompt.

First, whether you start the prompt right after the triple quotes or on the line below does not matter for formatting:


Code
Output

import outlines

@outlines.prompt
def prompt1():
    """My prompt
    """

@outlines.prompt
def prompt2():
    """
    My prompt
    """

print(prompt1())
print(prompt2())

Indentation is relative to the second line of the docstring, and leading spaces are removed:


Code
Output

import outlines

@outlines.prompt
def example1():
    """First line
    Second line
    """

@outlines.prompt
def example2():
    """
      Second line
      Third line
    """

@outlines.prompt
def example3():
    """
      Second line
        Third line
    """

print(example1())
print(example2())
print(example3())

Trailing whitespaces are not removed, unless they follow a linebreak symbol \ (see linebreaks).

Linebreaks
You can use the backslash \ to break a long line of text. It will render as a single line:


Code
Output

import outlines

@outlines.prompt
def example():
   """
   Break in \
   several lines \
   But respect the indentation
       on line breaks.
   And after everything \
   Goes back to normal
   """

print(example())

Llama.cpp
Installation

You need to install the llama-cpp-python library to be able to use these models in Outlines.

Outlines provides an integration with Llama.cpp using the llama-cpp-python library. Llamacpp allows to run quantized models on machines with limited compute.

You can initialize the model by pasing the path to the weights on your machine. Assuming Phi2's weights are in the current directory:


from outlines import models

model = models.llamacpp("./phi-2.Q4_K_M.gguf", device="cuda")
If you need more control, you can pass the same keyword arguments to the model as you would pass in the llama-ccp-library:


from outlines import models

model = models.llamacpp(
    "./phi-2.Q4_K_M.gguf",
    n_gpu_layers=-1,  # to use GPU acceleration
    seed=1337,  # to set a specific seed
)
Please see the llama-cpp-python documentation for a list of available keyword arguments. Finally, if for some reason you would like to initialize llama_cpp.Llama separately, you can convert it to an Outlines model using:


from llama_cpp import Llama
from outlines import models

llm = Llama.from_pretrained(
    repo_id="Qwen/Qwen1.5-0.5B-Chat-GGUF",
    filename="*q8_0.gguf",
    verbose=False
)
model = models.LlamaCpp(llm)




Models
TransformerTokenizer
Bases: Tokenizer

Represents a tokenizer for models in the transformers library.

Source code in outlines/models/transformers.py
Transformers
Represents a transformers model.

Source code in outlines/models/transformers.py
forward(input_ids, attention_mask, past_key_values=None)
Compute a forward pass through the transformer model.

PARAMETERS
input_ids The input token ids. Must be one or two dimensional. attention_mask The attention mask. Must be one or two dimensional. past_key_values A tuple of tuples containing the cached key and value tensors for each attention head.

RETURNS
The computed logits and the new cached key and value tensors.

Source code in outlines/models/transformers.py
get_llama_tokenizer_types()
Get all the Llama tokenizer types/classes that need work-arounds.

When they can't be imported, a dummy class is created.

Source code in outlines/models/transformers.py
transformers(model_name, device=None, model_kwargs={}, tokenizer_kwargs={})
Instantiate a model from the transformers library and its tokenizer.

Parameters
model_name The name of the model as listed on Hugging Face's model page. device The device(s) on which the model should be loaded. This overrides the device_map entry in model_kwargs when provided. model_kwargs A dictionary that contains the keyword arguments to pass to the from_pretrained method when loading the model. tokenizer_kwargs A dictionary that contains the keyword arguments to pass to the from_pretrained method when loading the tokenizer.

Returns
A TransformersModel model instance.

Source code in outlines/models/transformers.py
Integration with OpenAI's API.

OpenAI
An object that represents the OpenAI API.

Source code in outlines/models/openai.py
__call__(prompt, max_tokens=None, stop_at=None, *, system_prompt=None, temperature=None, samples=None)
Call the OpenAI API to generate text.

PARAMETERS
prompt A string or list of strings that will be used to prompt the model max_tokens The maximum number of tokens to generate stop_at A string or array of strings which, such that the generation stops when they are generated. system_prompt The content of the system message that precedes the user's prompt. temperature The value of the temperature used to sample tokens samples The number of completions to generate for each prompt stop_at Up to 4 words where the API will stop the completion.

Source code in outlines/models/openai.py
__init__(client, config, tokenizer=None, system_prompt=None)
Create an OpenAI instance.

This class supports the standard OpenAI API, the Azure OpeanAI API as well as compatible APIs that rely on the OpenAI client.

PARAMETERS
client An instance of the API's async client. config An instance of OpenAIConfig. Can be useful to specify some parameters that cannot be set by calling this class' methods. tokenizer The tokenizer associated with the model the client connects to.

Source code in outlines/models/openai.py
generate_choice(prompt, choices, max_tokens=None, system_prompt=None)
Call the OpenAI API to generate one of several choices.

PARAMETERS
prompt A string or list of strings that will be used to prompt the model choices The list of strings between which we ask the model to choose max_tokens The maximum number of tokens to generate system_prompt The content of the system message that precedes the user's prompt.

Source code in outlines/models/openai.py
generate_json()
Call the OpenAI API to generate a JSON object.

Source code in outlines/models/openai.py
OpenAIConfig dataclass
Represents the parameters of the OpenAI API.

The information was last fetched on 2023/11/20. We document below the properties that are specific to the OpenAI API. Not all these properties are supported by Outlines.

Properties
model The name of the model. Available models can be found on OpenAI's website. frequence_penalty Number between 2.0 and -2.0. Positive values penalize new tokens based on their existing frequency in the text, logit_bias Modifies the likelihood of specified tokens to appear in the completion. Number between -100 (forbid) and +100 (only allows). n The number of completions to return for each prompt. presence_penalty Similar to frequency penalty. response_format Specifies the format the model must output. {"type": "json_object"} enables JSON mode. seed Two completions with the same seed value should return the same completion. This is however not guaranteed. stop Up to 4 words where the API will stop the completion. temperature Number between 0 and 2. Higher values make the output more random, while lower values make it more deterministic. top_p Number between 0 and 1. Parameter for nucleus sampling. user A unique identifier for the end-user.

Source code in outlines/models/openai.py
build_optimistic_mask(transposed, max_mask_size=300)
We build the largest mask possible.

Tokens are added from left to right, so if the encoded choices are e.g. [[1,2], [3,4]], 1 and 3 will be added before 2 and 4.

Parameters
transposed A list of lists that contain the nth token of each choice.

Source code in outlines/models/openai.py
error_handler(api_call_fn)
Handle OpenAI API errors and missing API key.

Source code in outlines/models/openai.py
find_longest_intersection(response, choice)
Find the longest intersection between the response and the choice.

Source code in outlines/models/openai.py
find_response_choices_intersection(response, choices)
Find the longest intersection between the response and the different choices.

Say the response is of the form [1, 2, 3, 4, 5] and we have the choices [[1, 2], [1, 2, 3], [6, 7, 8] then the function will return [1, 2, 3] as the intersection, and [[]] as the list of choices left.

Parameters
response The model's response choices The remaining possible choices

Returns
A tuple that contains the longest intersection between the response and the different choices, and the choices which start with this intersection, with the intersection removed.

Source code in outlines/models/openai.py
generate_chat(prompt, system_prompt, client, config) async
Call OpenAI's Chat Completion API.

Parameters
prompt The prompt we use to start the generation. Passed to the model with the "user" role. system_prompt The system prompt, passed to the model with the "system" role before the prompt. client The API client config An OpenAIConfig instance.

Returns
A tuple that contains the model's response(s) and usage statistics.


Prompts
Prompt dataclass
Represents a prompt function.

We return a Prompt class instead of a simple function so the template defined in prompt functions can be accessed.

Source code in outlines/prompts.py
__call__(*args, **kwargs)
Render and return the template.

RETURNS
The rendered template as a Python str.

Source code in outlines/prompts.py
get_fn_description(fn)
Returns the first line of a callable's docstring.

Source code in outlines/prompts.py
get_fn_name(fn)
Returns the name of a callable.

Source code in outlines/prompts.py
get_fn_signature(fn)
Return the signature of a callable.

Source code in outlines/prompts.py
get_fn_source(fn)
Return the source code of a callable.

Source code in outlines/prompts.py
get_schema_dict(model)
Return a pretty-printed dictionary

Source code in outlines/prompts.py
get_schema_pydantic(model)
Return the schema of a Pydantic model.

Source code in outlines/prompts.py
parse_pydantic_schema(raw_schema, definitions)
Parse the output of Basemodel.[schema|model_json_schema]().

This recursively follows the references to other schemas in case of nested models. Other schemas are stored under the "definitions" key in the schema of the top-level model.

Source code in outlines/prompts.py
prompt(fn)
Decorate a function that contains a prompt template.

This allows to define prompts in the docstring of a function and simplify their manipulation by providing some degree of encapsulation. It uses the render function internally to render templates.

import outlines

@outlines.prompt def build_prompt(question): ... "I have a ${question}" ... prompt = build_prompt("How are you?")

This API can also be helpful in an "agent" context where parts of the prompt are set when the agent is initialized and never modified later. In this situation we can partially apply the prompt function at initialization.

import outlines import functools as ft ... @outlines.prompt ... def solve_task(name: str, objective: str, task: str): ... '''Your name is {{name}}. .. Your overall objective is to {{objective}}. ... Please solve the following task: {{task}} ... ''' ... hal = ft.partial(solve_task, "HAL", "Travel to Jupiter")

Returns
A Prompt callable class which will render the template when called.

Source code in outlines/prompts.py
render(template, **values)
Parse a Jinaj2 template and translate it into an Outlines graph.

This function removes extra whitespaces and linebreaks from templates to allow users to enter prompts more naturally than if they used Python's constructs directly. See the examples for a detailed explanation.

Examples
Outlines follow Jinja2's syntax

import outlines outline = outlines.render("I like {{food}} and {{sport}}", food="tomatoes", sport="tennis") I like tomatoes and tennis

If the first line of the template is empty, render removes it

from outlines import render

tpl = ''' ... A new string''' tpl ... '\nA new string' render(tpl) ... 'a new string'

Similarly, render ignores linebreaks introduced by placing the closing quotes underneath the text:

tpl = ''' ... A new string ... ''' tpl ... '\nA new string\n' render(tpl) ... 'A new string'

If you want to insert a linebreak at the end of the rendered template, you will need to leave an empty line at the end of the template:

tpl = ''' ... A new string ... ... ''' tpl ... '\nA new string\n\n' render(tpl) ... 'A new string\n'

render removes the identation in docstrings. This is particularly important when using prompt functions

tpl = ''' ... a string ... and another string''' tpl ... '\n a string\n and another string' render(tpl) ... 'a string\nand another string'

The indentation of the first line is assumed to be the same as the second line's

tpl = '''a string ... and another''' tpl ... 'a string\n and another' render(tpl) ... 'a string\nand another'

To get a different indentation for the first and the second line, we can start the prompt on the string's second line:

tpl = ''' ... First line ... Second line''' render(tpl) ... 'First Line\n Second Line'

Parameters
template A string that contains a template written with the Jinja2 syntax. **values Map from the variables in the template to their value.

Returns
A string that contains the rendered template.

Source code in outlines/prompts.py


Json schema
build_regex_from_schema(schema, whitespace_pattern=None)
Turn a JSON schema into a regex that matches any JSON object that follows this schema.

JSON Schema is a declarative language that allows to annotate JSON documents with types and descriptions. These schemas can be generated from any Python datastructure that has type annotation: namedtuples, dataclasses, Pydantic models. And by ensuring that the generation respects the schema we ensure that the output can be parsed into these objects. This function parses the provided schema and builds a generation schedule which mixes deterministic generation (fixed strings), and sampling with constraints.

Parameters

schema A string that represents a JSON Schema. whitespace_pattern Pattern to use for JSON syntactic whitespace (doesn't impact string literals) Example: allow only a single space or newline with whitespace_pattern=r"[ ]?"

Returns

A generation schedule. A list of strings that represent the JSON schema's structure and regular expression that define the structure of the fields.

References

.. [0] JSON Schema. https://json-schema.org/

Source code in outlines/fsm/json_schema.py
get_schema_from_signature(fn)
Turn a function signature into a JSON schema.

Every JSON object valid to the output JSON Schema can be passed to fn using the ** unpacking syntax.

Source code in outlines/fsm/json_schema.py
to_regex(resolver, instance, whitespace_pattern=None)
Translate a JSON Schema instance into a regex that validates the schema.

Note

Many features of JSON schema are missing: - Handle additionalProperties keyword - Handle types defined as a list - Handle constraints on numbers - Handle special patterns: date, uri, etc.

This does not support recursive definitions.

Parameters

resolver An object that resolves references to other instances within a schema instance The instance to translate whitespace_pattern Pattern to use for JSON syntactic whitespace (doesn't impact string literals) Example: allow only a single space or newline with whitespace_pattern=r"[ ]?"

Source code in outlines/fsm/json_schema.py

Guide
CFGGuide
Bases: Guide

Guide to generate text that is in the language of a context-free grammar.

Source code in outlines/fsm/guide.py
copy()
Create a copy of the FSM.

Source code in outlines/fsm/guide.py
get_next_instruction(state)
Generate an instruction for the next step.

Upon initialization, the CFG incremental parser is used to determine the first regex and construct the first FSM to generate the first terminal.

This FSM is used for proposals until either:

The FSM is exhausted, and its only remaining option is the EOS token, in which case we feed the generated terminal to the CFG incremental parser and allow it to propose the next regex corresponding to the next set of valid terminals.
The current FSM can be exhausted, but the EOS token is not the only remaining option. In this case we allow proposal of current terminal extensions, store the current FSM and its state, then also use the CFG parser to propose a new regex corresponding to terminating the current terminal and starting the next one. The model can then sample from either of these sets to determine whether to extend the current terminal or terminate it and start the next one.
The CFG incremental parser is allowed to propose the EOS token from any accepting state, and once it is generated, the FSM will continue to always generate the EOS token.

PARAMETERS
state The current state of the FSM.

RETURNS
A list that contains the tokens to mask.

Source code in outlines/fsm/guide.py
get_next_state(state, token_id)
Update the state of the guide.

Transitions the underlying regex FSM to its next state. If at max tokens or EOS token, transition permanently to the final state. Update stored partial generations for subsequent incremental parsing.

PARAMETERS
state The current state of the FSM. token_id The id of the token that was just generated.

RETURNS
The new state of the FSM.

Source code in outlines/fsm/guide.py
Generate dataclass
Generate instruction

Attributes
tokens The tokens that lead to a valid completion if generated.

Source code in outlines/fsm/guide.py
Guide
Bases: Protocol

Base definition of a generation guide.

A generation guide defines the behavior of a finite-state machine that guides a text generation procedure. Unlike the DFAs built from regular expressions guides can also emit a Write instructions which tells the model that it can append a sequence of tokens (or token word) instead of generating it.

Source code in outlines/fsm/guide.py
RegexGuide
Bases: Guide

Guide to generate text in the language of a regular expression.

Source code in outlines/fsm/guide.py
__init__(regex_string, tokenizer)
Source code in outlines/fsm/guide.py
get_next_instruction(state)
Return the next instruction for guided generation.

The initialization of the guide builds an index which maps FSM states to a map from authorized tokens to the state in which the guide needs to move if said token is generated. Therefore the authorized tokens at the current state are the keys of the map returned by the value of the index for current state.

If the current state is not contained in the end this means that we are in a final state of the guide. We only authorize EOS tokens in the final state.

PARAMETERS
state The current state of the guide.

RETURNS
A Generate instance that contains the model and the allowed token ids.

Source code in outlines/fsm/guide.py
get_next_state(state, token_id)
Update the state of the guide.

We use the index to determine to which state the guide should transition given the token that was just generated.

PARAMETERS
state The current state of the guide. token_id The id of the token that was just generated.

RETURNS
The new state of the guide.

Source code in outlines/fsm/guide.py
is_final_state(state)
Determine whether the current state of the guide is a final state.

Source code in outlines/fsm/guide.py
StopAtEOSGuide
Bases: Guide

Guide to generate tokens until the EOS token has been generated.

Source code in outlines/fsm/guide.py
__init__(tokenizer)
Initialize the generation guide.

model The logit generator used to generate the next token.

Source code in outlines/fsm/guide.py
Write dataclass
Write instruction.

Attributes
tokens The sequence of tokens to be added to the current sequence by the generation process.

Source code in outlines/fsm/guide.py


Parsing
PartialIndenter
Bases: Indenter

An Indenter that doesn't reset its state every time process is called.

Source code in outlines/fsm/parsing.py
PartialParserState
Bases: ParserState

Source code in outlines/fsm/parsing.py
feed_token_no_stack(token, is_end=False)
This is a copy of ParserState.feed_token with all the value stack steps removed. Since we're not exactly parsing in order to obtain a CST or anything similar, we can avoid the growing expense of tracking the parse tree.

Source code in outlines/fsm/parsing.py
PartialParsingFrontend
Bases: ParsingFrontend

Source code in outlines/fsm/parsing.py
PartialScanner
Bases: Scanner

Source code in outlines/fsm/parsing.py
get_terminals_info(fsm_state_seq)
Get the possible terminal symbols for an FSM state sequence.

Source code in outlines/fsm/parsing.py
match(text, pos, last_fsm_state_seq=None)
Determine an FSM match over text starting at pos and continuing last_fsm_state_seq.

Source code in outlines/fsm/parsing.py
terminals_to_fsms(lp)
Construct a dict mapping terminal symbol names to their finite state machines.

Source code in outlines/fsm/parsing.py

Regex
regex(model, regex_str, sampler=multinomial())
Generate structured text in the language of a regular expression.

Parameters
model: An instance of Transformer that represents a model from the transformers library. regex_str: The regular expression that the output must follow. sampler: The sampling algorithm to use to generate token ids from the logits distribution.

Returns
A SequenceGenerator instance that generates text constrained by the regular expression.

Source code in outlines/generate/regex.py

Samplers
BeamSearchSampler
Beam Search sampling algorithm.

Attributes
samples The number of samples taken for each input sequence.

Source code in outlines/samplers.py
__call__(next_token_logits, sequence_weights, _)
Call the beam search sampler.

PARAMETERS
next_token_logits A tensor of shape (n_seqs, vocab_size,) that represents the probability distribution of the next token over the vocabulary. sequence_weights A tensor of shape (n_seqs,) that represents the cumulative weight of each sequence. rng A random number generator.

RETURNS
A tuple with an array that contains the ids of the sampled tokens of shape (n_seqs, 1), an array that contains the ancestors of each sampled id of shape (n_seqs,) and an array that contains the updated cumulative weights of each sequence of shape (n_seqs,).

Source code in outlines/samplers.py
GreedySampler
Greedy Sampling algorithm.

Greedy sampling consists in choosing the token with the largest likelihood at every step.

We don't allow more than one sample. We could attribute this a meaning, for instance the k-th sample represents the k-th most likely token. In which case it would be equivalent to beam search without the sequence weights.

Attributes
samples The number of samples taken for each input sequence.

Source code in outlines/samplers.py
__call__(next_token_logits, sequence_weights, _)
Call the greedy sampler.

PARAMETERS
next_token_logits A tensor of shape (n_seqs, vocab_size,) that represents the probability distribution of the next token over the vocabulary. sequence_weights A tensor of shape (n_seqs,) that represents the cumulative weight of each sequence. rng A random number generator.

RETURNS
A tuple with an array that contains the ids of the sampled tokens of shape (n_seqs, 1), an array that contains the ancestors of each sampled id of shape (n_seqs,) and an array that contains the updated cumulative weights of each sequence of shape (n_seqs,).

Source code in outlines/samplers.py
MultinomialSampler
Multinomial sampling algorithm.

Multinomial sampling consists in randomly sampling the next token assuming its distribution is a Categorical distribution parametrized by the next-token logits.

Attributes
samples The number of samples taken for each input sequence.

Source code in outlines/samplers.py
__call__(next_token_logits, sequence_weights, rng)
Call the multinomial sampler.

PARAMETERS
next_token_logits A tensor of shape (n_seqs, vocab_size,) that represents the probability distribution of the next token over the vocabulary. sequence_weights A tensor of shape (n_seqs,) that represents the cumulative weight of each sequence. rng A random number generator.

RETURNS
A tuple with an array that contains the ids of the sampled tokens of shape (n_seqs, 1), an array that contains the ancestors of each sampled id of shape (n_seqs,) and an array that contains the updated cumulative weights of each sequence of shape (n_seqs,).

Source code in outlines/samplers.py
keep_top_k_logits(k)
Build a function that masks logits values smaller than the top k ones.

Parameters
k The ranking below which logit values are replaced by -math.inf.

Source code in outlines/samplers.py
keep_top_p_logits(p)
Build a function that masks the lowest probability tokens whose cumulative probability is below a certain threshold.

Parameters
p The value of the threshold. We keep the highest probability tokens whose cumulative distribution is greater than or equal to p and mask the others. Its value must be between 0 (excluded) and 1 (included).

Source code in outlines/samplers.py
rescale_logits(temperature)
Build a function that rescales the token probabilities exponentially.

Parameters
temperature The value by which we rescale the logits.

Source code in outlines/samplers.py