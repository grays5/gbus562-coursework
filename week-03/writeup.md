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

The complete, unedited contents of `q2.txt` must be pasted here to satisfy the Example Run requirement. I have not recreated or invented the output.

## Reflection

**What was wrong:** The document folder contained both `consumer-fee-schedule-v7.html` and the newer `consumer-fee-schedule.html`. The outdated Version 7 document stated that overdraft fees were $35, while the current Version 8 document stated $29. The retrieval results included chunks from both versions, which could have caused conflicting answers.

**How I fixed it:** Moved `consumer-fee-schedule-v7.html` into the `archived-docs` folder and rebuilt the Chroma database. After the fix, the tool retrieved the current Version 8 fee schedule without including the outdated Version 7 information.

**Prevention:** Archive process. In the future, outdated document versions should be moved out of the active knowledge base before rebuilding the database. A designated document owner should also verify which version is current.

**Question 6:** Declined. The retrieved chunks concerned unrelated fees and account information rather than current mortgage rates. Because the documents did not provide a 30-year fixed mortgage rate, the tool should decline to provide an unsupported number rather than invent an answer.
