**GBUS 562 Week 2: Prompting Techniques with Wildframe Coffee Roasters**

## What I Built

I built a Prompt Lab, a single-file web app (`week-02/prompt-lab.html`) for testing prompting techniques with Claude. It has a field for pasting an Anthropic API key each session. The key is never saved or stored in the code. It also has a System Prompt field and a conversation area that supports follow-up messages. A New Conversation button clears the history, and an Export button downloads the conversation as a Markdown file. The export puts the model name on the first line, then each message under `### System`, `### You` or `### Claude`.

I then did four prompting exercises for Wildframe Coffee Roasters, a fictional specialty coffee roaster whose voice is warm, plainspoken and slightly irreverent. **These four exercises were done in Claude Code, not in the Prompt Lab.** There was no API key available in the session, so each prompt was run in its own fresh, separate Claude Code conversation. The four conversations are saved in `week-02/runs/` as `task-1-claude-code-conversation.md` through `task-4-claude-code-conversation.md`. They are not Prompt Lab exports. They didn't use the Prompt Lab's model, and the Wildframe description was sent at the top of each message labeled "System:" instead of as a real system prompt. Each file explains this at the top, and the prompts and responses are copied word for word.

## Why This Approach

Task 1 - Technique: zero-shot
Task 1 asked for six creative subscriber perks, which is open-ended brainstorming with no single right answer. Zero-shot fits because giving examples could have pushed Claude toward copying them instead of coming up with new ideas. It was also a good baseline to see what Claude does with only a brand description and format rules. Claude followed the format exactly (6 numbered one-sentence ideas, 18 to 22 words each), but it made up details I never gave it. These included refillable "tins" (the Brand Kit says the bag is compostable), a "reforestation partner," "micro-lot releases," and experimental roasts "we're too nervous to sell publicly."

Task 2 - Technique: one-shot
Task 2 was about producing bean cards in a fixed format, so the main goal was matching an exact structure. One example is enough for that because it shows the labels, their order and the capitalized origin name all at once. Claude matched the Huila card's structure on all three cards and used the exact tasting notes I gave it. A couple of lines still added small unsupported claims, like Cerrado's "the bag empties fast."

Task 3 - Technique: few-shot
Task 3 was replying to customer comments, where tone and judgment matter more than format. A single example would only show one kind of situation, but three examples showed how Wildframe handles a skeptical question, a complaint and a compliment. Claude followed every rule (3 replies of 31, 27 and 23 words, no emoji). It also didn't invent order status, refunds or products. For the late order it asked for the order number instead of making up a tracking update.

Task 4 - Technique: chain-of-thought
Task 4 was a math-based business decision with a budget limit, which is easy to get wrong if you jump straight to an answer. Asking for step-by-step reasoning makes Claude show each calculation so I can check it, instead of trusting just the final recommendation. I checked the math and it was all correct. Riverside nets $6,480, Union Station is −$4,400 and over budget at $8,000 in rent, and Campus nets $1,200. The response ended with the one required line, "Recommendation: Riverside Farmers Market."

## Example Run

Below is the complete contents of my saved Task 3 file, `week-02/runs/task-3-claude-code-conversation.md`, pasted exactly as saved. **This is a Claude Code conversation, not a Prompt Lab export.** It's shown in a code block so its own headings don't mix with this writeup's headings.

````markdown
# Task 3 — Few-shot (Claude Code conversation, NOT a Prompt Lab export)

> **Source:** This run was NOT made with the Prompt Lab or the Anthropic API, and it is not a Prompt Lab export. No API key was available, so it was run as a fresh, separate Claude Code subagent conversation with no shared context from the other tasks. The model is not the Prompt Lab's configured model.
>
> **How the prompt was delivered:** Claude Code subagents can't take a separate system prompt, so the System text below was sent at the top of the same message, labeled `System:`, and the prompt was labeled `User:`. This instruction was added first so the reply would contain only the answer: "Do not use any tools. Your final message must contain only your answer to the message below, with no preamble or commentary."
>
> The prompt and response below are copied verbatim.

### System

Wildframe Coffee Roasters is a fictional specialty coffee roaster selling beans online and by monthly subscription. Its voice is warm, plainspoken, slightly irreverent, and free of corporate jargon. Its customers are environmentally conscious urban professionals.

### You

Brand Kit examples:

Comment: Is your packaging actually recyclable, or is that just marketing?
Reply: Fair question. The bag is compostable, the little valve isn't, so pop the valve off first. We're working on that last bit.

Comment: Your Kenya roast tasted burnt to me.
Reply: That's not the cup we were going for. Tell us how you brewed it and we'll help you dial it in, or swap you to something mellower.

Comment: Best coffee I've had in years!!
Reply: This made our whole roasting crew's morning. We'll keep doing the thing.

Reply to these customer comments in Wildframe's voice:
1. My order was supposed to arrive Monday. It's Thursday.
2. Do you make any decaf that doesn't taste like cardboard?
3. The Huila is my new Sunday morning ritual. Thank you.

Respond with exactly 3 numbered replies, each no more than 40 words, without emoji. Don't invent order status, refunds, or products not confirmed by the Brand Kit.

### Claude

1. Monday to Thursday is not the plan, and we're sorry. Send us your order number and we'll find out where your coffee got stuck and figure out next steps with you.

2. Fair ask. Decaf that tastes like cardboard is a crime. Send us a message and we'll tell you straight what we've got right now. No sales fluff.

3. Huila on a Sunday morning sounds just right to us. Thanks for making it part of the ritual. The roasting crew is grinning.
````

## Reflection

Comparing the four techniques, the clearest difference was between zero-shot and the techniques with examples. Zero-shot followed my formatting rules perfectly, but it filled gaps with believable details that weren't true for Wildframe, like the refillable tins and the tree-planting partner. One-shot was great for copying an exact structure. Few-shot did the best job of capturing the brand's voice and judgment, because the three examples showed how Wildframe talks in different situations. Its rule against inventing order status or products kept the replies honest. Chain-of-thought was the most useful for checking work, since I could verify every number myself. Even so, it added an assumption that farmers market shoppers "take their time," which wasn't in the data.

The choice I'm least sure of is using zero-shot for Task 1. I picked it to get original ideas, but since it produced the most unsupported claims, a one-shot prompt with a short list of real Wildframe facts might have worked better. The trade-off is that an example could make the ideas less creative. I also only ran each prompt once, so I can't say how consistent these results are. Going forward, I'd use few-shot prompts for on-brand marketing copy and chain-of-thought for budget decisions, and I'd always fact-check anything that sounds like a promise to customers.
