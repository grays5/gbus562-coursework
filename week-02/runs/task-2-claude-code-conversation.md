# Task 2 — One-shot (Claude Code conversation, NOT a Prompt Lab export)

> **Source:** This run was NOT made with the Prompt Lab or the Anthropic API, and it is not a Prompt Lab export. No API key was available, so it was run as a fresh, separate Claude Code subagent conversation with no shared context from the other tasks. The model is not the Prompt Lab's configured model.
>
> **How the prompt was delivered:** Claude Code subagents can't take a separate system prompt, so the System text below was sent at the top of the same message, labeled `System:`, and the prompt was labeled `User:`. This instruction was added first so the reply would contain only the answer: "Do not use any tools. Your final message must contain only your answer to the message below, with no preamble or commentary."
>
> The prompt and response below are copied verbatim.

### System

Wildframe Coffee Roasters is a fictional specialty coffee roaster selling beans online and by monthly subscription. Its voice is warm, plainspoken, slightly irreverent, and free of corporate jargon. Its customers are environmentally conscious urban professionals.

### You

Brand Kit example:

HUILA, COLOMBIA
Roast: Medium
Tastes like: red apple, brown sugar, cocoa
Brew it: Pour-over or drip
Real talk: The coffee that converted our office's tea drinker. Mostly.

Following the example's exact labels and order, create bean cards for:
Yirgacheffe, Ethiopia — Light; jasmine, lemon, bergamot; pour-over.
Cerrado, Brazil — Medium-dark; peanut, milk chocolate, low acidity; espresso or French press.
Chiapas, Mexico — Medium; almond, caramel, orange peel; drip or AeroPress.

### Claude

YIRGACHEFFE, ETHIOPIA
Roast: Light
Tastes like: jasmine, lemon, bergamot
Brew it: Pour-over
Real talk: It's basically a cup of Earl Grey that went to coffee school. Drink it slowly. It's worth it.

CERRADO, BRAZIL
Roast: Medium-dark
Tastes like: peanut, milk chocolate, low acidity
Brew it: Espresso or French press
Real talk: A peanut butter cup you can drink, so it's no surprise the bag empties fast. Easy on your stomach, easy on your Monday.

CHIAPAS, MEXICO
Roast: Medium
Tastes like: almond, caramel, orange peel
Brew it: Drip or AeroPress
Real talk: The one we hand to friends who say they "just like normal coffee." Then they start asking where to buy it.
