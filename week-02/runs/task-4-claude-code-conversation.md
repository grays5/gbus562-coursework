# Task 4 — Chain-of-thought (Claude Code conversation, NOT a Prompt Lab export)

> **Source:** This run was NOT made with the Prompt Lab or the Anthropic API, and it is not a Prompt Lab export. No API key was available, so it was run as a fresh, separate Claude Code subagent conversation with no shared context from the other tasks. The model is not the Prompt Lab's configured model.
>
> **How the prompt was delivered:** Claude Code subagents can't take a separate system prompt, so the System text below was sent at the top of the same message, labeled `System:`, and the prompt was labeled `User:`. This instruction was added first so the reply would contain only the answer: "Do not use any tools. Your final message must contain only your answer to the message below, with no preamble or commentary."
>
> The prompt and response below are copied verbatim.

### System

Wildframe Coffee Roasters is a fictional specialty coffee roaster selling beans online and by monthly subscription. Its voice is warm, plainspoken, slightly irreverent, and free of corporate jargon. Its customers are environmentally conscious urban professionals.

### You

Use the following data to compare the locations. Show the calculations and a concise step-by-step explanation of the decision.

Riverside Farmers Market: 9,000 visitors/week, 2% purchase, $14 average sale, $900 weekly rent.
Union Station concourse: 30,000 visitors/week, 0.5% purchase, $6 average sale, $2,000 weekly rent.
Campus library atrium: 6,000 visitors/week, 3% purchase, $5 average sale, $600 weekly rent.

The pop-up lasts four weeks and has a maximum total rent budget of $5,000. Calculate expected four-week sales, total rent, and sales minus rent. Recommend one location. End the response with exactly one line beginning Recommendation: followed by the location name.

### Claude

Here's how the three spots compare over the four-week pop-up.

**Step 1: Weekly buyers (visitors × purchase rate)**
- Riverside Farmers Market: 9,000 × 2% = 180 buyers
- Union Station concourse: 30,000 × 0.5% = 150 buyers
- Campus library atrium: 6,000 × 3% = 180 buyers

**Step 2: Weekly sales (buyers × average sale)**
- Riverside: 180 × $14 = $2,520
- Union Station: 150 × $6 = $900
- Campus: 180 × $5 = $900

**Step 3: Four-week totals**

| Location | 4-week sales | 4-week rent | Sales minus rent | Within $5,000 budget? |
|---|---|---|---|---|
| Riverside Farmers Market | $2,520 × 4 = **$10,080** | $900 × 4 = **$3,600** | **$6,480** | Yes |
| Union Station concourse | $900 × 4 = **$3,600** | $2,000 × 4 = **$8,000** | **−$4,400** | No (over by $3,000) |
| Campus library atrium | $900 × 4 = **$3,600** | $600 × 4 = **$2,400** | **$1,200** | Yes |

**Step 4: Decision**
1. **Check the budget.** Union Station's rent is $8,000, which is over the $5,000 limit. It also loses $4,400, so it's out on both counts.
2. **Compare the two that fit.** Riverside and Campus both get 180 buyers a week. Riverside's average sale is $14 against Campus's $5, so it brings in nearly three times the sales.
3. **Look at what's left after rent.** Riverside nets $6,480 and Campus nets $1,200. Riverside costs $1,200 more in rent but earns $6,480 more in sales.
4. **Check the fit.** Farmers market shoppers come to buy local and take their time. That suits customers who care where their coffee comes from, and it explains the higher average sale (whole bags, not just a cup).

Riverside makes the most money, fits the budget with $1,400 to spare, and reaches the right customers.

Recommendation: Riverside Farmers Market
