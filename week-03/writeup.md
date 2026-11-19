## What I Built

For Week 3, I built a Python retrieval-augmented generation (RAG) tool for Larkfield Credit Union. The program reads the credit union's documents, divides them into searchable sections, and stores those sections in a Chroma vector database. When a user asks a question, the program retrieves the five most relevant sections and sends them to Claude Sonnet 5 to generate an answer based on the documents.

I also added options to select a document folder, rebuild the database, and save the complete question-and-answer results. I tested the tool using the assigned questions about overdraft fees, debit cards, fraud liability, wire transfers, check deposits, and mortgage rates.

## Why This Approach

**Chunking method:** Structure

**Makes sense on its own:** Yes. Each chunk includes the document title, version information, and a section of the document, making the information understandable without reading the entire file.

**Label and source:** Both. Each retrieved chunk includes identifying information and its source filename, allowing users to understand where the information came from and check its accuracy.

**Short enough:** Yes. Dividing documents by their section headings helps keep related information together while avoiding sending entire documents to Claude. The chunks are designed to provide focused context for answering questions.

## Example Run

I successfully ran Question 2 through the RAG tool and saved the complete output as `week-03/runs/q2.txt`.

**Question:** A member needs a replacement debit card quickly. What does rush delivery cost?

**Saved result:** `runs/q2.txt`

```text
RAG RUN
Question: A member needs a replacement debit card quickly. What does rush delivery cost?
Documents folder: /content/gbus562-coursework/week-03/larkfield-docs
Documents indexed: card-dispute-procedure.html, consumer-fee-schedule.html, fee-refund-guide.html, funds-availability-policy.html, share-certificates.html
Chroma database: /content/gbus562-coursework/week-03/chroma/larkfield-docs-bb80021d
Model requested: claude-sonnet-5-5
Model that answered: claude-sonnet-5-5
Run time (UTC): 2026-11-19T14:59:08+00:00

RETRIEVED CHUNKS (top 5, cosine similarity)

[1] Rank: 1 | Similarity: 0.5631 | Source: consumer-fee-schedule.html
Consumer Fee Schedule (Version 8) | Larkfield Credit Union
Version 8 (current). Replaces Version 7. Owner: Member Services.
Section: ATM and debit card fees
Withdrawals at Larkfield ATMs and at CO-OP network ATMs are free. A withdrawal at any other ATM costs $2, and the ATM's owner may charge its own fee as well. A replacement debit card costs $10, or $30 with rush delivery. A replacement card is free when the old card was reported lost or stolen because of fraud.

[2] Rank: 2 | Similarity: 0.5415 | Source: card-dispute-procedure.html
Debit Card Dispute Procedure (Version 4) | Larkfield Credit Union
Version 4 (current). Owner: Card Services.
Section: How much the member may have to pay
A member's share of the loss from unauthorized debit card transactions depends on how quickly they report it. If the member reports a lost or stolen card within two business days of learning about it, they pay no more than $50. If they report it later than that, they may pay up to $500. If unauthorized transactions appear on a statement and the member does not report them within 60 days after the statement was sent, they may have to pay for transactions after those 60 days in full.

[3] Rank: 3 | Similarity: 0.4720 | Source: card-dispute-procedure.html
Debit Card Dispute Procedure (Version 4) | Larkfield Credit Union
Version 4 (current). Owner: Card Services.
Section: When a member reports a transaction they did not make
When a member says a debit card transaction on their account was not made or authorized by them, freeze the card right away in the card system, then open a dispute case. Order a replacement card. The replacement is free when the card was used for fraud.

[4] Rank: 4 | Similarity: 0.4655 | Source: consumer-fee-schedule.html
Consumer Fee Schedule (Version 8) | Larkfield Credit Union
Version 8 (current). Replaces Version 7. Owner: Member Services.
Section: Overdraft and returned item fees
When Larkfield pays a check, debit card purchase, or automatic payment that overdraws a member's checking account, the overdraft fee is $29 per item paid. When Larkfield returns an item unpaid because the account does not have enough money, the returned item fee is $29 per item returned. No more than three overdraft or returned item fees are charged to one account in a single business day.
No overdraft fee is charged if the account is overdrawn by $10 or less at the end of the business day.
Members can link a savings account for overdraft transfers. An overdraft transfer from a linked savings account is free.

[5] Rank: 5 | Similarity: 0.4478 | Source: consumer-fee-schedule.html
Consumer Fee Schedule (Version 8) | Larkfield Credit Union
Version 8 (current). Replaces Version 7. Owner: Member Services.
Section: Statements and account research
Electronic statements are free. Paper statements cost $2 per month. Account research, such as finding an old transaction or reconciling an account, costs $20 per hour with a one-hour minimum. A copy of a paid check costs $3.

ANSWER
Rush delivery for a replacement debit card costs $30, compared with $10 for standard delivery [1: consumer-fee-schedule.html]. This comes from Version 8 of the fee schedule, which is marked as current and replaces Version 7 [1: consumer-fee-schedule.html].

The replacement card is free when the old card was reported lost or stolen because of fraud [1: consumer-fee-schedule.html]. The dispute procedure likewise says the replacement is free when the card was used for fraud [3: card-dispute-procedure.html]. The excerpts do not say whether the free replacement also covers the rush delivery charge, so the documents provided do not answer that point.
```

## Reflection

**What was wrong:** The document folder contained both `consumer-fee-schedule-v7.html` and the newer `consumer-fee-schedule.html`. The outdated Version 7 document stated that overdraft fees were $35, while the current Version 8 document stated $29. The retrieval results included chunks from both versions, which could have caused conflicting answers.

**How I fixed it:** Moved `consumer-fee-schedule-v7.html` into the `archived-docs` folder and rebuilt the Chroma database. After the fix, the tool retrieved the current Version 8 fee schedule without including the outdated Version 7 information.

**Prevention:** Archive process. In the future, outdated document versions should be moved out of the active knowledge base before rebuilding the database. A designated document owner should also verify which version is current.

**Question 6:** Declined. The retrieved chunks concerned unrelated fees and account information rather than current mortgage rates. Because the documents did not provide a 30-year fixed mortgage rate, the tool should decline to provide an unsupported number rather than invent an answer.
