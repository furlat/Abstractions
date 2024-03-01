This want to be a package/repository of [[Pydantic]] Models that can be used as abstraction of real world artifacts in generative ai workwflows.  The intended utilization is together with [[Cynde]] 

The general Idea introduced by tools like Instructor or Guidance, and more in general the function calling methods introduced by open ai api, is to constrain llm decoding using grammar constrained generation. 

The best workflow goes from  Prompt + Pydantic Model --> JsonString Template--> Regex --> state-machine -->  generated JsonString --> decoded PydanticModel l

Now we will proceed with some Abstaction codeblocks, describing a book as a nested model of chapters, paragraphs, sentences,words:  

