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
