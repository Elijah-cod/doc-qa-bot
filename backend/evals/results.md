# Retrieval eval

_2026-10-01 · embed model `gemini-embedding-001` (768 dims) · chunk 500 tok · top_k 5_

16 answerable questions, 6 off-topic questions, fictional 6-page handbook.

| Metric | Value |
|---|---|
| Hit rate @1 | 100% |
| Hit rate @5 | 100% |
| MRR | 1.000 |
| Top score, answerable (min / avg) | 0.610 / 0.683 |
| Top score, off-topic (max / avg) | 0.668 / 0.546 |

**Recommended `SCORE_CUTOFF=0.56`**: answers 100% of real questions, blocks 83% of off-topic ones. (Current setting: 0.6)

| Cutoff | Real questions answered | Off-topic blocked |
|---|---|---|
| 0.40 | 100% | 0% |
| 0.42 | 100% | 0% |
| 0.44 | 100% | 0% |
| 0.46 | 100% | 0% |
| 0.48 | 100% | 0% |
| 0.50 | 100% | 17% |
| 0.52 | 100% | 33% |
| 0.54 | 100% | 67% |
| 0.56 ← | 100% | 83% |
| 0.58 | 100% | 83% |
| 0.60 | 100% | 83% |
| 0.62 | 94% | 83% |
| 0.64 | 81% | 83% |
| 0.66 | 56% | 83% |
| 0.68 | 50% | 100% |
| 0.70 | 44% | 100% |
| 0.72 | 31% | 100% |
| 0.74 | 12% | 100% |
| 0.76 | 0% | 100% |
| 0.78 | 0% | 100% |
| 0.80 | 0% | 100% |

## Answers: 22/22 correct

| | Question | Answer |
|---|---|---|
| ✅ | When was the company founded and by whom? | Northwind Robotics was founded in 2014 by Amina Odhiambo and Lars Becker [1]. |
| ✅ | How many staff does Northwind have? | Northwind Robotics employs 340 people across its offices in Nairobi, Berlin, and Toronto [1]. |
| ✅ | What is the throughput of the Sorter X2? | The Sorter X2 can move up to 1,200 parcels per hour [1]. |
| ✅ | How many vacation days do I get each year? | Full-time employees receive 24 days of paid annual leave per calendar year, plus local public holidays [1]. |
| ✅ | Can I roll over unused holiday to next year? | Yes, up to 5 unused days of paid annual leave may be carried over to the next year, while any additional unused days beyond that will expire on 31 March [1]. |
| ✅ | How long is parental leave? | Parental leave is 16 weeks at full pay for all parents, regardless of gender [1]. |
| ✅ | What cabin class can I fly on a long-haul trip? | For flights longer than six hours, employees may book premium economy [1]. |
| ✅ | What is the hotel budget per night in London? | The hotel cost reimbursement limit in London is 220 US dollars per night [1]. |
| ✅ | How do I get reimbursed for travel costs? | To get reimbursed for travel costs, you must submit all expense claims through the Ledgerly app within 30 days of the trip, with photos of every receipt attache |
| ✅ | What are the password requirements? | Passwords must be at least 14 characters long and are stored in the company password manager, Vaultkeep [1]. |
| ✅ | What should I do if my laptop gets stolen? | If your laptop gets stolen, you must report it to the security team within one hour by emailing security@northwind.example [1]. |
| ✅ | What is the project codename for the delivery robot? | The internal codename for the delivery robot is BLUEHERON [1]. |
| ✅ | Who leads the outdoor delivery robot project? | The outdoor delivery robot project (Project BLUEHERON) is led by Dr. Wanjiru Kamau [1]. |
| ✅ | How heavy a parcel can the new delivery robot carry? | The new delivery robot, BLUEHERON, can carry parcels of up to 25 kilograms [1]. |
| ✅ | When is lunch served at the office? | The cafeteria serves free lunch between 12pm and 2pm on weekdays [1]. |
| ✅ | How do guests get into the building? | Visitors must be registered at reception at least one day in advance and must wear a visitor badge at all times [1]. |
| ✅ | What is the capital of France? | I couldn't find that in the document. |
| ✅ | How do I bake sourdough bread? | I couldn't find that in the document. |
| ✅ | Who won the 2022 football World Cup? | I couldn't find that in the document. |
| ✅ | What is Northwind's current stock price? | I couldn't find that in the document. |
| ✅ | What is the salary of a junior engineer? | I couldn't find that in the document. |
| ✅ | Explain how photosynthesis works. | I couldn't find that in the document. |
