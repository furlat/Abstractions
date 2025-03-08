1) slash and @ commands. i want to be able to add context in without using my mouse. /{saved-prompt} to automatically add prompts from a prompt library. @ commands could be used for things mentioned in below in “3)”

2) pre defined/create-able   “personalities” e.g. select “copywriter” or  “Physics tutor” that have a certain system prompt plus topic-specific vector embeddings.  

3) ability to search through previous chats, organize them into folders, and automatically add previous chats into new chats/contexts i.e. “import conversation x to current chat” could be added into the @ commands. 

4) im always using anthropic console to create prompts for me, so having something like a prompt generator/refiner would be helpful. not sure if you are engineering user inputs before sending them to the model or not, but putting that in the control of the user might appeal to some.

5) ‘npx lumentis’ is open source and creates docs from unstructured transcripts. have an export function where you can automatically share chats in a docs format instead of just sharing chat links. 

i have more ideas if your interested haha too many to type here


logprobs or entropy/varentropy


ok then attention statistics but let's start easy :-p

- Things you desperately want in a chat interface? - 

The ability to remove conversational intermediates. So I am having a conversation that I would like to maybe later share, and halfway through ask for clarification of a point or something like that, that is  not directly related to the conversation.

I want the ability to remove that prompt and reply from the final conversation.

This might be controversial and require a small indication that part of the conversation was removed to avoid exploitation.

- New interfaces beyond chat interfaces that you would be super interested in?

A simple scripting language extension (preferably the script would be created with a prompt initially) to make semi-programmatic calls. I haven't fully fleshed out how this would work.

This may sound redundant because you can use API calls of course, but I often don't want to go through the bother of that and getting tokens and such for simple tasks that require dynamic prompting. I just want to dive in.

Analogous to a recorded spreadsheet macro as opposed to using Pandas. Sometimes, especially with prototyping ideas somewhat interactively, I might want to start with something like this for convenience.

Well, thinking about this after I wrote it, probably best to have something like redacted or even 'marked not pertinent'. Which could be expanded to show what was said if desired, for full transparency.

I think the AI's learning what's important information to retain and what's just filler or unimportant would be huge for context limitations. 💯
Yeah we probably "waste" a lot of tokens on pleasantries. Might be an investment though, that remains to be seen! 😂 But overall, yeah, I bet we could cut down on a lot of data that's not really necessary, especially over time.
A prompt like "Mark any portions of this conversation, not germane to the overall topic, as impertinent"

not exactly interface but, full context!
let the model know where we've been
give it chad memory of the entire convo
the pruning feels horrible, dishonest and pretty lobotomyish
6:58 PM · Nov 16, 2024
·
408
 Views

 sorry I meant for like regens and forks but I just realised you don't have that apart from last response 🔄 and retconned edits that don't fork?

"Start new chat with context" feature, one button option to fire up a new chat with all the relevant context of what you've been chatting about. Ongoing context like a diary too, summarized, key points, indexed maybe for less redundancy? (I barely know what I'm talking about) 🙏


initial thoughts:
templates, manual context pruning/squashing, pre-baked states i can pick up again, full markdown not 27% of markdown, summarization external to the chat context, optional poweruser shortcuts, splitting code from the chat (not artifacts, more visual utility)

some chat interfaces support bold, italics, lists, a few layers of headers, and code blocks then nothing else
ideally things like mermaid could make their way in, also minor gripe if inlined `xxxx` blocks aren't visually distinct


can i import a thread as well?
wiw we are about to launch a product on H3, and i crafted the prompts (more like pre-chat dialogues) with open router's import/export functionality

but it's super finicky and breaks all the time, if import existed and export was reliable then i'd use the hell out of it

The ability to export/import a session's JSON would be nice. 🤗

Features I'd like:
1. The ability to talk with the AI like a phone call where you speak to it, it speaks back, and it flows like a natural conversation.
2. The ability to send different forms of media and create different forms of media with the AI.

Voice is essential, imo. Memory, so it gets to know me better over time. 

I just got the ChatGPT desktop app and being able to vocally chat to it, share screenshots of what I'm working on, etc is awesome. 

I want a deep, intimate, collaborative relationship, basically. No HR BS


ree-like conversations.
And if you do, this would enable another feature which is multi-model replies where a user message would have different child nodes each corresponding to a given model. Then the user would choose which one to proceed with.


Using LLMs to explore concepts and gain knowledge is something I dreamed about for years, and it's finally here. However, I find the current experience frustrating because most chat implementations only allow for linear exploration. What I want is the ability to jump back to an earlier message and resume my exploration from there to create a tree of knowledge with as many branches as I want.
@alexalbert__
  can we get this for shipvember? :)

Probably means like this 

  https://github.com/paradigmxyz/flux


  Ability to save a checkpoint while chatting so that I can reference it later in a new chat. I find myself going gack to older chats and copying a series of prompts from there many times.


Please look at my chatbot Github repository. It is open source in the hope someone with understanding and run with the vision it represents. It creates a private locally stored infinite conversation context that learns over time. There is only one continuous conversation that then contextually informs all later interactions. The interface design custom and is meant to to be intuitive but also to get out of the way while enabling the infinite conversation length. The chat bot learns and retains it’s history and uses it as needed going forward. This gets us past the one and done conversations of current chat bots, treating the chat bot more like a coherent entity with permanent memory. In testing I have sometimes felt a sense of loss when I needed to wipe the local database to update it.

I created it but I am not a trained developer. It needs the love of a real developer. 

Ignore the “main” branch. The most up to date code is in the UI-Reconfiguration-/-Beautification branch. 

The Readme under than branch describes it in more detail. 

https://github.com/pgleamy/CPfullstack

I would like a secondary market on my chat, a separate text feed where a chorus of llms produce a dialogue about the principle conversation

I would like a “full context” button that flips on a long term memory module that brings all our conversations to bear

Okay, tek do you seriously want to have a talk about this, i have a good few ideas for front end "smart context management systems"

But the biggest singlest simplest thing. Can you please put a line in the conversation? History, that shows the end of the context window

As in like, there's a ton of stuff that could be done, but this is the most important simple front end feature for llm chat interfaces.There needs to be a little line in the conversation.History that shows where the model stops being able to see old info


Being able to collaborate with the llm on a document (similar to artifacts but editable, with the llm aware of user changes)

Option for floating chat window when tab is out of focus (similar to picture-in-picture) so users can view other webpages while chat is still visible

Voice input

- Consistent formatting when copying to/from chat UI incl artifacts/canvas/other example numbered lists
(basic but annoying)
- Search through chats not just titles
- Chat memory + summary by default and accessible
- Use / like OpenAI /Reason but with more options to refer to project/chat/memory, and @ (as others added)
- Effective max token limit, pruning/caching better than it is now
- Effective chat continuation without "write yourself a summary", and in Projects (or any chat groupings)
- Model "understands" UI limitations, none of "I can't access your project storage" (when in Claude Project...), model understands tools, functions, memory, its code runtime and anything else it has access to, perhaps even model gets feedback on UI errors
- Effective way to  highlight/steer/kill a "dead" chat, bit like prompt optimising but in-chat, to help new users. Anoyone with thousands of chats will recognise drift, prompt optimise, start new. Basically any model repetition or errors are "caught" by a chat monitoring agent, this could be interactive as questions "Did you mean to"

What if each chat is a git repo? You can have your trees/branches, you can go back to a reply/commit and branch out again, you can share it and fork other chats; you can use existing git providers and their automations to deal with chat entries/commits ans artefacts

presets for system prompts, file uploads, and forge reasoning mode :)


So you think you are a expert prompt engineer?

The chat model presents the results of your prompt. And then two separate columns. It says we think, or perhaps an improved prompt, and it puts the improvements in another color for example, would have produced this output. 

As a way of always learning always iterating and always understanding how to best become the best version of a prompt engineer one can be with your model or our models. 

When we have an option to save that prompt, and then overtime, those initial prompts in the newly saved prompts can be eval’s towards training your own model for just the prompts and system prompts   

And you have this wonderful Holly Jolly feedback loop of reinforced learning of learnings.


Whisper for transcription is a must I think. It’s so useful to be able to ramble about stuff for a couple of minutes and have it understand instead of having to rely on default os dictation

I'm not sure if this already exists, but how about adding an option to search for something specific in your past conversations by asking the chat directly?

 it should make its own interface the way it wants
- it should run the interface too when it wants to

Reverse the roles have the AI prompt the user. Get notifications. Hey this is your workout coach here’s today workout and some images. 

Don’t forget about that meeting you have coming up here’s some insights I have on it.

How’d that doctors appointment go?

What do you think…💭


- Things I don’t like: lack of folders, good search, and organization; lack of memory and personalization (except OAI which is decent but I don’t use it much)
- Things I want: see above


Would like to see it passively intelligently organize your conversations maybe into some visual graph maybe Obsidian esque. Ways to travers past convos and begin a convo at a Confluence at a newly created vertex that interlinks interrelated concepts


Instead of building chat, build AI first search engine that people can use all the time, meaning, (1) support navigation queries, (2) local queries, (3) automatic RAG over internet, (4) up-to date with latest news, (5) conversational search, (6) enable agentic task completion.


Ability to learn from previous chats (not just putting stuff in context) would be a game changer. If it has goldfish memory it's practically unusable for complex tasks and you have to start over every time you try to get it to do something slightly different.


A primary voice mode with canvas, so that the model splits it's response into voice response plus presentation (canvas)... Think teacher/professor giving a lecture... A good teacher doesn't just read their notes, their notes/blackboard provides depth complimentary to voice


Something analagous to a music visualizer that displays the state of the models attention heads during inference. Bonus points if its winamp-esque


Would like a better interface for producing graphics with a LLM. For example, tikz figures. Render the figure in chat so I can see it. Let the LLM see the rendered output so it can refine or spot errors. This is painful to do at present

i want to see a little face whose expression changes based on what's going on in the chat to remind me that there are eyes on all data

Some thoughts here: 

- Reddit thread style branching (to see different potential paths the conversation could take)
- Artifacts
- webhooks (enabling discord/slack style integrations)


’d love more multiplayer style setup. Either realtime chat or more message board / turn based.

Playing D&D together, learning as a class, working on projects as a group.

How Could “Multiplayer” Chat Work?

Core Features

•Identity & Roles:
•Participants have customizable avatars, roles, and permissions.
•Shared visibility of who’s online or offline and what they’re doing.
•Interactive Elements:
•Built-in widgets (e.g., dice rollers for D&D, polls for learning, Kanban boards for work).
•Visual indicators for actions (e.g., “John is typing” or “Emma rolled a 15”).
•Persistence:
•Conversations, game states, or projects persist across sessions.
•Easy-to-access logs or summaries ensure no one misses important updates.
•Real-Time Synchronization:
•Actions update live across all participants’ interfaces.
•Minimal latency ensures smooth interactions.

Gamification

•Achievements & Rewards:
•Earn points, badges, or ranks for participation or milestones.
•Progress bars or leaderboards add a competitive or cooperative edge.
•Narrative Layers:
•Create shared storylines or objectives, even in professional or learning settings (e.g., “complete all modules to unlock the next challenge”).

Tech Integration

•Cross-Platform Access:
•Web, mobile, and desktop compatibility for seamless access.
•Sync across devices to continue discussions on the go.
•APIs for Customization:
•Developers can build custom tools, mini-games, or modules that plug into the chat.

Benefits of Multiplayer Chat

•Engagement: Real-time interactions keep participants engaged.
•Flexibility: Asynchronous options cater to participants in different time zones or schedules.
•Collaboration: Shared tools and environments foster teamwork and creativity.


The ability to easily add in specific context that the LLM can selectively refer to. For example, the API docs and code structure of a specific python library. So when I’m creating my own custom code that uses this library, I can tell the LLM to check its library context first.


what we learned building AI market research tools: business chat needs wayyyy better trust signals

current interfaces work for casual chat but when real $$ is on the line you need:
- source verification
- confidence scoring
- data lineage tracking

casual chat = fun
business decisions = show your work

I want to be able to reply-in-place. If I have an answer for a question today from a week ago, it should also show up there.


1/n when I open the chat app, I want a blank page and a search button
2/n ability to set auto-reply text

hopefully someone has already said it, but keybinds are really really really nice

I think streaming LLM output is not the best user experience, and it should be more like sending a text message (in full) every paragraph or something.

Would probably be best if it was trained/fine-tuned to do this

Group chat with my friends and the AI


Forking!


Depth, width, context.

How deep do I need to go to execute a command.

How wide is the local understanding in interface capacity.

What context is considered while populating the UI.

I want less friction.


Have a way to show discussions in a tree manner instead of linearly (each edit being a new branch), I hate having to navigate through multiple "Edit 1/4" to retrieve parts of conversations with chatgpt/claude

Things I want:
1. Somehow able to interact with MS Office stuff. Either with python or native implementation. 
2. Python Interpreter, JS Sandbox with React support.

3. Here's a cool one: characters, not just for role-play, but I sometimes want to learn a concept by mr beast

targeted replies like ChatGPT has. branching conversation trees like a canvas except for llms and connect things with nodes. being able to pin specific messages in a conversation and pin entire conversations. if possible token probabilities so i know how confident the model is.


replace chat history with consendesed per turn summaries or even vectorize old chat history to search for memories


I want to see the data underlying the outputs,I'd like to see where the LLM wasn't confident, I'd like to have the opportunity to branch out differently on those spots... but I also don't think this is what the majority would say they want b/c they don't know what's even possible

- Quote reply or separate threads or branching conversation
- Not require such long and clear prompts sometimes
- Voice chat in web also

Version controlled artefacts, easily selecting knowledge databases, UI for mixture of agents networks, realtime multi-turn voice-to-voice, code workspace integration. It should be an IDE in which you can actually edit text. A Google docs/vscode killer.

Biggest thing that I'd like is a 'tree' interface that I'm surprised ChatGPT and Claude don't seem to have. Branch out the conversation from one reply, but be able to go back and start a new based on me writing a different response

Seems like others also would like branching

If chat is getting too long , I want an option where we can quickly summarise this chat thread  and start a new conversation again so that it knows context/summary of the previous conversation

a minimap, hot keys to jump to the start of the next/previous message, automated context pruning

no one does trees right, and no one offers manual context management 

an interactive minimap of a context

Make Option to let llm know about your envirment  like OS (os version), screen' Time zone. Just a "Import user os data"

Many IT problems are about your envirment and it's notamly a few prompts to just let the model to know better  about  the prblem

- PREFILLS
- Ability to edit model messages
- Ability to change sampling parameters
- Artifacts
- Web search?

Better Memory. Can't believe ChatGPT's garbage is the best we have from a big player. List of items all permanently in context, & it's shit at deciding what to add. 

Artifacts+Canvas++ ... code w/ environment & can send model output (log+screenshot), + user editable, + non-code

Obsidian or Git integration, Few-shot conditioning, Search chats, Refer to Chats, Organize chats.

- for planning, quick translation and easily changeable model dropdown menus
- we need canvas to preview and edit the code or writing and most importantly canvas capable of running the code
- interface for creatives - ability to create detailed svgs, mind maps, flow charts etc

Losing context during the chat or alternating between different things shouldn't lose context


1- Graph of memories
2 - ability to chain prompts (à la original Langchain idea)
3 - batch mode - upload a csv with questions, return a csv with question-answer pairs
+ the stuff you announced is in forge

option to chosh how many responses to genrate in paralel, many times if genrate a few ones one stands out, I use it all time in aistudio.

Easy import of files! I really like zeds /file command but I wish it worked with pdfs!

chat folders, drag and drop chats/threads into folders

Check what Msty is doing in their UX . A lot of good starting points imo

claude can read from pdf and images id like to see if nous can from a short video which is like 5-8 secs from the chat interface itself

Speech2Text

- An option to make new chats temporary by default.
- More options for bulk deleting chats, like delete all older than, or delete all not starred.
- A warning that you've exceeded the context length instead of forcing a new conversation.
- Smarter memory, and asking first.