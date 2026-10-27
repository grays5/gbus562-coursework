**GBUS 562 Week 2: Prompting Techniques with Wildframe Coffee Roasters**

## What I Built

I built a Prompt Lab, a single-file web app (`week-02/prompt-lab.html`) that sends prompts to Claude through the Anthropic API using the model `claude-sonnet-5`. I paste my API key in each session, and it is never saved or written into the code. The app has a System Prompt field and a conversation area that supports follow-up messages. A New Conversation button clears the history. The Export button downloads the conversation as Markdown, with the model name on the first line and each message under `### System`, `### You` or `### Claude`.

I used the Prompt Lab to run four prompting exercises for Wildframe Coffee Roasters, a fictional specialty coffee roaster with a warm, plainspoken, slightly irreverent voice. Each task was its own conversation. The four Prompt Lab exports are saved unedited in `week-02/runs/` as `task-1.md` through `task-4.md`. (The `task-N-claude-code-conversation.md` files in the same folder are an earlier practice round done in Claude Code before I had the Prompt Lab working. They are not my submitted runs.)

One thing I noticed in the exports is that the System Prompts for Tasks 3 and 4, and the Task 3 user prompt, end with a stray line like "Copy System Prompt" or "Copy Task 3 Prompt." It looks like button text that got copied along with the prompts, so it was sent to Claude too. It didn't seem to affect the responses.

## Why This Approach

Task 1 - Technique: zero-shot
Task 1 asked for six subscriber perks, which is open-ended brainstorming, so I gave Claude only the brand description and format rules with no examples. I wanted to see what ideas it would come up with on its own without copying a template. It followed the format exactly: 6 numbered ideas, each one sentence of 17 to 23 words. But with no facts to work from, it assumed things Wildframe never confirmed. These include a "Roaster's Secret" blend, a loyalty points program ("Double loyalty points"), a "compostable canvas tote," the ability to swap roasts or delivery dates anytime, and "Ask a Roaster" hangouts.

Task 2 - Technique: one-shot
Task 2 was about matching a fixed card format, and one example is enough to show the labels, their order and the capitalized origin name. More examples weren't needed because the structure, not the judgment, was the hard part. Claude matched the Huila example on all three cards, with the name in uppercase and Roast, Tastes like, Brew it and Real talk in order. It also used the exact tasting notes and brew methods I gave it. The "Real talk" lines picked up the voice well, like Cerrado being "the coffee equivalent of a weighted blanket."

Task 3 - Technique: few-shot
Customer replies depend on tone and judgment, so I gave four example replies covering a skeptical question, a complaint, a compliment and a how-to question. Showing several situations teaches the voice better than one example would. The first response followed the format (3 numbered replies of 17 to 18 words, no emoji), but reply 2 invented a product detail: "Our decaf's swiss-water processed." I sent a follow-up telling Claude to revise only reply 2 without inventing product details. It removed the Swiss-water claim and kept replies 1 and 3 exactly the same.

Task 4 - Technique: chain-of-thought
Task 4 was a business decision with math and a $5,000 rent limit, so I asked Claude to work step by step and show each calculation. That way I could check every number instead of trusting just the recommendation. I checked all of it and it's correct. Riverside has 180 customers a week, $10,080 in four-week sales, $3,600 in rent and $6,480 sales minus rent. Union Station comes to −$4,400 and is over budget at $8,000 in rent, and the Campus library nets $1,200. Claude ruled out Union Station for the budget and ended with exactly one final line: "Recommendation: Riverside Farmers Market."

## Example Run

Below is the full, unedited contents of my Task 3 Prompt Lab export, `week-02/runs/task-3.md`, including the follow-up correction. It's shown in a code block so the export's own headings don't mix with this writeup's headings.

````markdown
claude-sonnet-5

### System

You are a customer service assistant for Wildframe Coffee Roasters, a specialty coffee roaster selling beans online and through monthly subscriptions. Write in a warm, plainspoken, slightly irreverent voice without corporate jargon. Customers are environmentally conscious urban professionals. Follow the user's instructions exactly. Do not invent company policies, order statuses, refunds, or products.
 Copy System Prompt

### You

Write customer replies for Wildframe Coffee Roasters using the same voice and style as these four examples from our past customer interactions.

Comment: Is your packaging actually recyclable, or is that just marketing?
Reply: Fair question. The bag is compostable, the little valve isn't, so pop the valve off first. We're working on that last bit.

Comment: Your Kenya roast tasted burnt to me.
Reply: That's not the cup we were going for. Tell us how you brewed it and we'll help you dial it in, or swap you to something mellower.

Comment: Best coffee I've had in years!!
Reply: This made our whole roasting crew's morning. We'll keep doing the thing.

Comment: Can I pause my subscription while I travel?
Reply: Yep. Account, then Subscription, then Pause. Your beans will wait for you, mostly patiently.

Now reply to these three new customer comments:

1. My order was supposed to arrive Monday. It's Thursday.
2. Do you make any decaf that doesn't taste like cardboard?
3. The Huila is my new Sunday morning ritual. Thank you.

Required format: Output exactly three replies, numbered 1 to 3, in the same order as the comments. Each reply must be no more than 40 words. Do not use emoji. Do not invent order statuses, refunds, company policies, or products. Output only the three numbered replies.
 Copy Task 3 Prompt

### Claude

1. Ugh, Thursday's not Monday. Send us your order number and we'll get to the bottom of it.

2. We hear you. Our decaf's swiss-water processed to keep the flavor intact, not just the caffeine removed.

3. Sunday mornings just got a nod from us too. Thanks for letting us be part of the ritual.

### You

Revise reply 2 only. The Brand Kit does not confirm that Wildframe sells Swiss-water-processed decaf, so do not invent product details. Keep all three numbered replies, each under 40 words, with no emojis. Output only the revised three replies.

### Claude

1. Ugh, Thursday's not Monday. Send us your order number and we'll get to the bottom of it.

2. We hear you, cardboard is nobody's ritual. Tell us what you've tried and we'll point you toward a decaf worth sipping.

3. Sunday mornings just got a nod from us too. Thanks for letting us be part of the ritual.
````

## Reflection

Comparing all four runs, the technique that helped most was few-shot. The four example replies in Task 3 gave Claude a clear sense of Wildframe's voice, and the replies sounded like the brand ("Ugh, Thursday's not Monday"). Few-shot still wasn't perfect, though. Task 3 initially invented a decaf processing detail, saying the decaf was "swiss-water processed," even though the system prompt said not to invent products. It improved after my follow-up, but the revised reply still says "we'll point you toward a decaf worth sipping," which kind of implies Wildframe sells decaf. One-shot worked really well in Task 2 because the goal was copying a structure, and one example was enough. Chain-of-thought in Task 4 was the easiest to trust because I could check every step. One thing to keep in mind is that it called sales minus rent "profit," even though that leaves out costs like beans and staff.

The choice I'm least certain about is using zero-shot for Task 1. It gave creative ideas in the right format, but it also made the most unsupported assumptions, like a loyalty points program and a "Roaster's Secret" blend. A one-shot prompt or a short list of real Wildframe facts might have kept it grounded. The biggest thing I learned is that AI output needs a fact check before it reaches customers, no matter which technique I use.
