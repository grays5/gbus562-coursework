# Week 2 Writeup: Prompting Techniques with Wildframe Coffee Roasters

## How These Runs Were Done

I built a Prompt Lab web app (`week-02/prompt-lab.html`) for this week that sends prompts to Claude through the Anthropic API and can export each conversation as Markdown. **I did not use the Prompt Lab for these four exercises.** There was no API key available in the session, so I had Claude Code run each prompt in its own fresh, separate conversation instead. The saved conversations are in `week-02/runs/`, named `task-1-claude-code-conversation.md` through `task-4-claude-code-conversation.md`. They are not Prompt Lab exports.

A few things are different because of that:

- The runs did not use the model the Prompt Lab is set to use.
- Claude Code conversations can't take a separate system prompt, so the Wildframe brand description was sent at the top of the same message, labeled "System:".
- One extra line was added before each prompt telling Claude not to use tools and to reply with only the answer.

Each file records these details, and the prompts and responses in them are copied word for word.

## The Four Techniques

- **Zero-shot:** You give the model a task and format rules but no examples. It has to guess what "good" looks like from the instructions alone.
- **One-shot:** You give one example of the output you want. The model copies its structure and tone.
- **Few-shot:** You give several examples. This shows the model a pattern across different situations, not just one template, so it can pick up the voice and judgment behind the examples.
- **Chain-of-thought:** You ask the model to work through the problem step by step and show its reasoning before giving an answer. This is useful for math and decisions because you can check each step.

## What Happened in Each Run

### Task 1: Zero-shot (subscriber perks)

I asked for exactly 6 perks for subscribers of six months or more, each one sentence of 25 words or less. Claude followed the format exactly: 6 numbered ideas, each one sentence, between 18 and 22 words. The voice matched the brand description pretty well. Lines like "you slurp loudly alongside our roasters" and "terrible puns are fully encouraged" sound warm and a little irreverent, not corporate.

The problem is that with no examples or facts to work from, Claude filled in details on its own. Perk 2 says "Send back your empty tins and we'll refill and reship them free." Nothing in the prompt says Wildframe uses tins. In fact, the Brand Kit examples from Task 3 say the bag is compostable. Perk 5 promises to "plant a tree with a reforestation partner and send you its GPS coordinates," but Wildframe doesn't have a reforestation partner in anything I gave it. Perk 1 assumes Wildframe sells "tiny micro-lot releases," and Perk 6 assumes there are experimental roasts "we're too nervous to sell publicly." None of that is confirmed. These might be fine brainstorming ideas, but a real marketing team would have to check every one before promising it to customers.

### Task 2: One-shot (bean cards)

I gave one example card for Huila, Colombia and asked for three more cards using the same labels in the same order. Claude got the structure right on all three. Each one has the origin name in capitals (like "YIRGACHEFFE, ETHIOPIA"), then Roast, Tastes like, Brew it and Real talk in that order. It also used the exact tasting notes and brew methods I gave it.

The "Real talk" lines were the creative part, and they were mostly good. The Yirgacheffe one, "It's basically a cup of Earl Grey that went to coffee school," is a smart way to explain bergamot to someone who doesn't know coffee. The Chiapas line about friends who "just like normal coffee" fits the voice of the example ("converted our office's tea drinker. Mostly."). Two small issues: the Cerrado card says "the bag empties fast," which is a claim about sales that wasn't in my data, and "Easy on your stomach" turns "low acidity" into something close to a health claim. The Yirgacheffe line also runs three sentences, while the example is shorter and punchier.

### Task 3: Few-shot (customer comment replies)

I gave three example comments and replies, then asked for replies to three new comments. Each reply had to be 40 words or less, with no emoji and no made-up order status, refunds or products. Claude followed every rule. The replies were 31, 27 and 23 words, with no emoji.

What stood out was that it stayed inside the guardrails. For the late order, it didn't invent a tracking update or offer a refund. It said "Send us your order number and we'll find out where your coffee got stuck," which is honest and still helpful. For the decaf question, it didn't claim Wildframe sells decaf, since that wasn't confirmed. It said "we'll tell you straight what we've got right now." The tone clearly picked up from the examples too. "Fair ask" echoes the example's "Fair question," and "The roasting crew is grinning" echoes "This made our whole roasting crew's morning."

The decaf reply is a little bit of a dodge, though. It's the right call given the rules, but a real customer might find it vague. That's a case where the business would need to give the AI real product information.

### Task 4: Chain-of-thought (pop-up location)

I gave data for three locations and asked Claude to calculate four-week sales, total rent and sales minus rent. It had to stay within a $5,000 rent budget and end with one "Recommendation:" line. Claude broke it into steps:

- Weekly buyers: for example, 9,000 × 2% = 180 at Riverside
- Weekly sales: 180 × $14 = $2,520
- A table of four-week totals

I checked the math and it's all correct:

| Location | 4-week sales | 4-week rent | Sales minus rent |
|---|---|---|---|
| Riverside Farmers Market | $10,080 | $3,600 | $6,480 |
| Union Station concourse | $3,600 | $8,000 | −$4,400 |
| Campus library atrium | $3,600 | $2,400 | $1,200 |

It ruled out Union Station first because $8,000 in rent is over the budget, then compared the other two. It ended with exactly one line, "Recommendation: Riverside Farmers Market," which is the right answer from the numbers.

One thing I noticed is that Step 4 adds reasoning that isn't in the data. It says farmers market shoppers "take their time" and that this "explains the higher average sale (whole bags, not just a cup)." That might be true, but it's an assumption. The recommendation still holds on the numbers alone, so it doesn't change the answer.

## What Worked and What Could Be Improved

**What worked:**
- Claude followed every format rule in all four tasks: exact counts, word limits, label order, no emoji and the final Recommendation line.
- Examples made a clear difference. In Tasks 2 and 3, the replies copied the structure and voice of the Brand Kit very closely.
- Stating what not to do worked. In Task 3, "Don't invent order status, refunds, or products" kept the replies honest.
- Asking for the steps in Task 4 made it easy to check the math myself instead of just trusting the answer.

**What could be improved:**
- The zero-shot run made unsupported assumptions: refillable tins, a reforestation partner, micro-lot releases and secret experimental roasts. Next time I would add a short list of real Wildframe facts (packaging, what's actually offered) and a rule like "only suggest perks that don't depend on products or partners we haven't confirmed."
- Even with examples, small invented details slipped into the creative lines, like "the bag empties fast" in Task 2. Anything that sounds like a fact should get a human check before it's published.
- In Task 4, I could tell Claude to base the decision only on the given data, or to label any extra reasoning as an assumption.
- I only ran each prompt once, so I can't tell how consistent the results are. Running the same prompt a few times, or running the same task with zero-shot and few-shot side by side, would be a fairer comparison.
- These runs didn't go through my Prompt Lab, so there are no Prompt Lab exports. To get them, I would need to run the four prompts in the Prompt Lab with my own API key and use its Export button.

## Reflection

The biggest thing I learned this week is that the prompt matters as much as the model. When I gave Claude no examples, it still followed my format perfectly, but it made up details about Wildframe that sounded believable and weren't true, like the refillable tins and the tree-planting partner. When I gave it examples, the output matched the brand much more closely, because the examples showed it what "warm and slightly irreverent" actually sounds like. I also learned that rules about what not to do are just as important as rules about what to do. The Task 3 replies stayed honest because the prompt said not to invent order status or products.

For future business and marketing work, I can see using few-shot prompts to write social media replies, product descriptions or email copy that stays on brand. I'd start by collecting a few strong examples to use as a template. Chain-of-thought seems most useful for decisions with numbers, like choosing a location or comparing budgets, because I can check each step instead of just trusting the answer. The main habit I want to keep is treating AI output as a first draft. I need to check any facts, prices or promises before they go in front of a customer, because a confident-sounding sentence isn't always a true one.
